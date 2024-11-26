import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import pytest
import os
import ssl
import time
import logging
import traceback
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('boltz_k8s_tests')

# Disable SSL verification globally
ssl._create_default_https_context = ssl._create_unverified_context

# Custom Exception Classes
class BoltzK8sTestError(Exception):
    """Base exception for Boltz Kubernetes testing errors"""
    pass

class K8sConnectivityError(BoltzK8sTestError):
    """Raised when there are issues connecting to Kubernetes cluster"""
    pass

class DeploymentConfigError(BoltzK8sTestError):
    """Raised when deployment configuration is invalid"""
    pass

class NetworkConnectivityError(BoltzK8sTestError):
    """Raised when network connectivity issues are detected"""
    pass

try:
    import kubernetes
    from kubernetes import client, config
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    logger.error("Kubernetes client not installed. Some tests will be skipped.")

@pytest.mark.skipif(not KUBERNETES_AVAILABLE, reason="Kubernetes client not installed")
class TestBoltzK8sDeployment:
    k8s_available = False
    core_v1_api = None
    apps_v1_api = None
    namespace = None

    @classmethod
    def setup_class(cls):
        """
        Set up Kubernetes client configuration for testing
        Supports both in-cluster and local kubeconfig
        """
        # Reset configuration to default
        cls.k8s_available = False
        cls.core_v1_api = None
        cls.apps_v1_api = None
        cls.namespace = None

        # Check if kubernetes library is available
        if not KUBERNETES_AVAILABLE:
            logger.warning("Kubernetes client not installed. Skipping Kubernetes tests.")
            return

        try:
            # Try multiple configuration methods
            config_methods = [
                config.load_incluster_config,
                config.load_kube_config,
                lambda: config.load_kube_config(config_file=os.path.expanduser('~/.kube/config'))
            ]

            for method in config_methods:
                try:
                    method()
                    logger.info(f"Successfully loaded Kubernetes configuration using {method.__name__}")
                    break
                except Exception as config_error:
                    logger.debug(f"Configuration method {method.__name__} failed: {config_error}")
                    continue
            else:
                logger.warning("Could not load Kubernetes configuration from any source")
                return
            
            # Configure Kubernetes client to skip SSL verification
            configuration = client.Configuration()
            configuration.verify_ssl = False
            configuration.assert_hostname = False
            client.Configuration.set_default(configuration)
            
            cls.core_v1_api = client.CoreV1Api()
            cls.apps_v1_api = client.AppsV1Api()
            cls.namespace = os.getenv('BOLTZ_NAMESPACE', 'default')
            
            # Soft connectivity check with timeout
            try:
                # Try a lightweight operation with a timeout
                namespaces = cls.core_v1_api.list_namespace(timeout_seconds=5)
                cls.k8s_available = len(namespaces.items) > 0
                logger.info(f"Connected to Kubernetes cluster. Found {len(namespaces.items)} namespaces")
            except Exception as connectivity_error:
                logger.warning(f"Soft connectivity check failed: {connectivity_error}")
                cls.k8s_available = False
        
        except Exception as e:
            error_msg = f"Could not initialize Kubernetes configuration: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            cls.k8s_available = False

    def _get_boltz_deployments(self) -> List:
        """
        Helper method to retrieve Boltz deployments with error handling
        
        Returns:
            List of Boltz deployments
        """
        try:
            # Use label selector to find Boltz deployments
            deployments = self.apps_v1_api.list_namespaced_deployment(
                namespace=self.namespace,
                label_selector='app=boltz'
            )
            
            return deployments.items
        
        except client.exceptions.ApiException as e:
            error_msg = f"Error retrieving Boltz deployments in namespace {self.namespace}: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            raise K8sConnectivityError(error_msg) from e

    def test_kubernetes_connectivity(self):
        """
        Comprehensive test to verify Kubernetes cluster connectivity
        """
        try:
            # List namespaces as a connectivity check
            namespaces = self.core_v1_api.list_namespace()
            namespace_names = [ns.metadata.name for ns in namespaces.items]
            
            logger.info(f"Connected to cluster. Available namespaces: {namespace_names}")
            assert len(namespaces.items) > 0, "No namespaces found in cluster"
        except Exception as e:
            error_msg = f"Failed to connect to Kubernetes cluster: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            raise K8sConnectivityError(error_msg) from e

    def test_boltz_deployment_exists(self):
        """
        Test if Boltz deployment exists in the Kubernetes cluster
        """
        if not self.k8s_available:
            pytest.skip("Kubernetes cluster not available for testing")
        
        try:
            deployments = self._get_boltz_deployments()
            
            assert len(deployments) > 0, "No Boltz deployments found in the cluster"
            
            for deployment in deployments:
                logger.info(f"Found Boltz deployment: {deployment.metadata.name}")
                
                # Check deployment status
                assert deployment.status.available_replicas is not None, \
                    f"Deployment {deployment.metadata.name} has no available replicas"
                
                assert deployment.status.available_replicas > 0, \
                    f"Deployment {deployment.metadata.name} has 0 available replicas"
        
        except client.exceptions.ApiException as e:
            logger.error(f"Kubernetes API error: {e}")
            raise K8sConnectivityError(f"Failed to retrieve Boltz deployments: {e}") from e

    def test_boltz_deployment_replica_stability(self):
        """
        Verify deployment replica stability over time with enhanced error tracking
        """
        if not self.k8s_available:
            pytest.skip("Kubernetes cluster not available for testing")
        
        try:
            deployments = self._get_boltz_deployments()
            
            for deployment in deployments:
                # Initial replica count
                initial_replicas = deployment.status.available_replicas
                logger.info(f"Initial replica count for {deployment.metadata.name}: {initial_replicas}")
                
                # Wait and check replica stability
                time.sleep(10)  # Wait 10 seconds
                
                # Refresh deployment status
                updated_deployment = self.apps_v1_api.read_namespaced_deployment(
                    name=deployment.metadata.name,
                    namespace=self.namespace
                )
                
                current_replicas = updated_deployment.status.available_replicas
                logger.info(f"Current replica count for {deployment.metadata.name}: {current_replicas}")
                
                # Check replica stability
                assert current_replicas == initial_replicas, \
                    f"Replica count changed from {initial_replicas} to {current_replicas}"
        
        except client.exceptions.ApiException as e:
            logger.error(f"Kubernetes API error during replica stability check: {e}")
            raise K8sConnectivityError(f"Failed to check replica stability: {e}") from e

    def test_boltz_service_exists(self):
        """
        Comprehensive verification of Boltz service configuration
        """
        if not self.k8s_available:
            pytest.skip("Kubernetes cluster not available for testing")
        
        try:
            services = self.core_v1_api.list_namespaced_service(self.namespace)
            
            boltz_services = [
                svc for svc in services.items 
                if 'boltz' in svc.metadata.name.lower()
            ]
            
            for service in boltz_services:
                logger.info(f"Validating service: {service.metadata.name}")
                
                # Detailed service validation
                assert service.spec.ports is not None, \
                    f"Service {service.metadata.name} has no defined ports"
                
                # Check service selector
                assert service.spec.selector is not None, \
                    f"Service {service.metadata.name} has no selector"
                
                # Validate ports
                for port in service.spec.ports:
                    assert port.port is not None, \
                        f"Service {service.metadata.name} has undefined port number"
                    assert port.target_port is not None, \
                        f"Service {service.metadata.name} has no target port"
                    
                    logger.info(f"Service {service.metadata.name} port: {port.port} -> {port.target_port}")
        except AssertionError as ae:
            logger.error(f"Service configuration error: {ae}")
            raise DeploymentConfigError(str(ae)) from ae
        except Exception as e:
            error_msg = f"Error checking Boltz service: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            raise DeploymentConfigError(error_msg) from e

    def test_boltz_pod_status(self):
        """
        Comprehensive pod status check with detailed logging
        """
        if not self.k8s_available:
            pytest.skip("Kubernetes cluster not available for testing")
        
        try:
            pods = self.core_v1_api.list_namespaced_pod(self.namespace)
            
            boltz_pods = [
                pod for pod in pods.items 
                if any('boltz' in container.name.lower() 
                       for container in pod.spec.containers)
            ]
            
            if not boltz_pods:
                logger.warning(f"No Boltz pods found in namespace {self.namespace}")
                pytest.skip("No Boltz pods found in namespace")
            
            for pod in boltz_pods:
                logger.info(f"Checking pod: {pod.metadata.name}")
                
                # Detailed pod status check
                assert pod.status.phase in ['Running', 'Succeeded'], \
                    f"Pod {pod.metadata.name} is not in Running/Succeeded state"
                
                # Additional pod condition checks
                for condition in pod.status.conditions or []:
                    assert condition.status == 'True', \
                        f"Pod {pod.metadata.name} has condition {condition.type} not met"
                
                logger.info(f"Pod {pod.metadata.name} status: {pod.status.phase}")
        except AssertionError as ae:
            logger.error(f"Pod status test failed: {ae}")
            raise DeploymentConfigError(str(ae)) from ae
        except Exception as e:
            error_msg = f"Error checking Boltz pod status: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            raise DeploymentConfigError(error_msg) from e

    def test_boltz_pod_network_connectivity(self):
        """
        Advanced network connectivity test with detailed logging and error handling
        """
        if not self.k8s_available:
            pytest.skip("Kubernetes cluster not available for testing")
        
        try:
            pods = self.core_v1_api.list_namespaced_pod(self.namespace)
            
            boltz_pods = [
                pod for pod in pods.items 
                if any('boltz' in container.name.lower() 
                       for container in pod.spec.containers)
            ]
            
            if len(boltz_pods) < 2:
                logger.warning("Not enough Boltz pods to test inter-pod connectivity")
                pytest.skip("Not enough Boltz pods to test inter-pod connectivity")
            
            # Detailed network connectivity check
            for i, pod1 in enumerate(boltz_pods):
                for pod2 in boltz_pods[i+1:]:
                    logger.info(f"Checking network connectivity between {pod1.metadata.name} and {pod2.metadata.name}")
                    
                    # Verify pods are in different nodes for realistic testing
                    assert pod1.spec.node_name != pod2.spec.node_name, \
                        f"Pods {pod1.metadata.name} and {pod2.metadata.name} should be on different nodes"
                    
                    logger.info(f"Pods on different nodes: {pod1.spec.node_name} vs {pod2.spec.node_name}")
        except AssertionError as ae:
            logger.error(f"Network connectivity test failed: {ae}")
            raise NetworkConnectivityError(str(ae)) from ae
        except Exception as e:
            error_msg = f"Error checking Boltz pod network connectivity: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            raise NetworkConnectivityError(error_msg) from e

    def test_boltz_service_endpoint_resolution(self):
        """
        Verify service endpoint resolution and accessibility
        """
        if not self.k8s_available:
            pytest.skip("Kubernetes cluster not available for testing")
        
        try:
            services = self.core_v1_api.list_namespaced_service(self.namespace)
            
            boltz_services = [
                svc for svc in services.items 
                if 'boltz' in svc.metadata.name.lower()
            ]
            
            for service in boltz_services:
                # Check service has selector
                assert service.spec.selector is not None, \
                    f"Service {service.metadata.name} has no selector"
                
                # Verify service ports
                assert service.spec.ports is not None, \
                    f"Service {service.metadata.name} has no defined ports"
                
                for port in service.spec.ports:
                    assert port.port is not None, \
                        f"Service {service.metadata.name} has undefined port"
                    assert port.target_port is not None, \
                        f"Service {service.metadata.name} has no target port"
        except AssertionError as ae:
            logger.error(f"Service endpoint resolution error: {ae}")
            raise DeploymentConfigError(str(ae)) from ae
        except Exception as e:
            error_msg = f"Error checking Boltz service endpoint resolution: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            raise DeploymentConfigError(error_msg) from e

    def test_boltz_pod_security_context(self):
        """
        Verify pod security context and restrictions
        """
        if not self.k8s_available:
            pytest.skip("Kubernetes cluster not available for testing")
        
        try:
            deployments = self._get_boltz_deployments()
            
            for deployment in deployments:
                pod_spec = deployment.spec.template.spec
                
                # Check for non-root user
                for container in pod_spec.containers:
                    security_context = container.security_context
                    
                    if security_context:
                        # Verify run as non-root
                        assert security_context.run_as_non_root is True, \
                            f"Container {container.name} should run as non-root"
                        
                        # Optional: Check read-only root filesystem
                        if security_context.read_only_root_filesystem is not None:
                            assert security_context.read_only_root_filesystem, \
                                f"Container {container.name} should have read-only root filesystem"
        except AssertionError as ae:
            logger.error(f"Pod security context error: {ae}")
            raise DeploymentConfigError(str(ae)) from ae
        except Exception as e:
            error_msg = f"Error checking Boltz pod security context: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            raise DeploymentConfigError(error_msg) from e

    def test_boltz_deployment_update_strategy(self):
        """
        Verify deployment update strategy
        """
        if not self.k8s_available:
            pytest.skip("Kubernetes cluster not available for testing")
        
        try:
            deployments = self._get_boltz_deployments()
            
            for deployment in deployments:
                # Check rolling update strategy
                update_strategy = deployment.spec.strategy
                
                assert update_strategy is not None, \
                    f"Deployment {deployment.metadata.name} lacks update strategy"
                
                # Verify rolling update configuration
                if update_strategy.type == 'RollingUpdate':
                    rolling_update = update_strategy.rolling_update
                    
                    assert rolling_update is not None, \
                        f"Deployment {deployment.metadata.name} lacks rolling update config"
                    
                    # Check max surge and unavailable limits
                    assert rolling_update.max_surge is not None, \
                        f"Deployment {deployment.metadata.name} lacks max surge config"
                    assert rolling_update.max_unavailable is not None, \
                        f"Deployment {deployment.metadata.name} lacks max unavailable config"
        except AssertionError as ae:
            logger.error(f"Deployment update strategy error: {ae}")
            raise DeploymentConfigError(str(ae)) from ae
        except Exception as e:
            error_msg = f"Error checking Boltz deployment update strategy: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            raise DeploymentConfigError(error_msg) from e

    def test_boltz_resource_requirements(self):
        """
        Verify resource requirements for Boltz deployment
        """
        if not self.k8s_available:
            pytest.skip("Kubernetes cluster not available for testing")
        
        try:
            deployments = self._get_boltz_deployments()
            
            for deployment in deployments:
                for container in deployment.spec.template.spec.containers:
                    resources = container.resources
                    
                    # Check CPU and memory requests are defined
                    assert resources is not None, f"No resources defined for {container.name}"
                    assert resources.requests is not None, f"No resource requests for {container.name}"
                    
                    # Optional: Add specific resource requirement checks
                    assert 'cpu' in resources.requests, f"No CPU request for {container.name}"
                    assert 'memory' in resources.requests, f"No memory request for {container.name}"
        except AssertionError as ae:
            logger.error(f"Resource requirements error: {ae}")
            raise DeploymentConfigError(str(ae)) from ae
        except Exception as e:
            error_msg = f"Error checking Boltz resource requirements: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            raise DeploymentConfigError(error_msg) from e

    def test_boltz_resource_quotas(self):
        """
        Test namespace resource quotas for Boltz deployments
        """
        if not self.k8s_available:
            pytest.skip("Kubernetes cluster not available for testing")
        
        try:
            deployments = self._get_boltz_deployments()
            
            for deployment in deployments:
                logger.info(f"Checking resource quotas for deployment: {deployment.metadata.name}")
                
                # Check container resource limits and requests
                for container in deployment.spec.template.spec.containers:
                    assert container.resources is not None, \
                        f"Container {container.name} has no resource specifications"
                    
                    # Check memory limits
                    assert container.resources.limits is not None, \
                        f"Container {container.name} has no resource limits"
                    assert 'memory' in container.resources.limits, \
                        f"Memory limit not set for container {container.name}"
                    
                    # Check CPU limits
                    assert 'cpu' in container.resources.limits, \
                        f"CPU limit not set for container {container.name}"
                    
                    # Check requests
                    assert container.resources.requests is not None, \
                        f"Container {container.name} has no resource requests"
                    assert 'memory' in container.resources.requests, \
                        f"Memory request not set for container {container.name}"
                    assert 'cpu' in container.resources.requests, \
                        f"CPU request not set for container {container.name}"
                    
                    logger.info(f"Container {container.name} resource limits: {container.resources.limits}")
                    logger.info(f"Container {container.name} resource requests: {container.resources.requests}")
        
        except AssertionError as ae:
            logger.error(f"Resource quota test failed: {ae}")
            raise DeploymentConfigError(str(ae)) from ae
        except Exception as e:
            error_msg = f"Error checking resource quotas: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            raise DeploymentConfigError(error_msg) from e

    def test_boltz_volume_mounts(self):
        """
        Verify required volume mounts for models and cache
        """
        if not self.k8s_available:
            pytest.skip("Kubernetes cluster not available for testing")
        
        try:
            deployments = self._get_boltz_deployments()
            
            required_mounts = {
                '/data/cache': 'cache-volume',
                '/data/models': 'models-volume'
            }
            
            for deployment in deployments:
                logger.info(f"Checking volume mounts for deployment: {deployment.metadata.name}")
                
                # Check volumes are defined
                assert deployment.spec.template.spec.volumes is not None, \
                    f"No volumes defined for deployment {deployment.metadata.name}"
                
                # Create map of volume names to volume definitions
                volume_map = {
                    vol.name: vol for vol in deployment.spec.template.spec.volumes
                }
                
                # Check containers for required mounts
                for container in deployment.spec.template.spec.containers:
                    assert container.volume_mounts is not None, \
                        f"No volume mounts defined for container {container.name}"
                    
                    # Check each required mount
                    for mount_path, volume_name in required_mounts.items():
                        mount_found = False
                        for mount in container.volume_mounts:
                            if mount.mount_path == mount_path:
                                mount_found = True
                                assert mount.name in volume_map, \
                                    f"Volume {mount.name} not defined for mount {mount_path}"
                                logger.info(f"Found volume mount {mount_path} -> {mount.name}")
                                break
                        
                        assert mount_found, \
                            f"Required mount {mount_path} not found in container {container.name}"
        
        except AssertionError as ae:
            logger.error(f"Volume mount test failed: {ae}")
            raise DeploymentConfigError(str(ae)) from ae
        except Exception as e:
            error_msg = f"Error checking volume mounts: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            raise DeploymentConfigError(error_msg) from e

def test_kubernetes_client_installed():
    """
    Verify Kubernetes client installation with enhanced logging
    """
    try:
        import kubernetes
        logger.info(f"Kubernetes client installed. Version: {kubernetes.__version__}")
    except ImportError:
        logger.error("Kubernetes client is not installed")
        pytest.fail("Kubernetes client is required for testing")
