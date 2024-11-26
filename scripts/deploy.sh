#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置信息
DOCKER_USERNAME="xingqiangchen"
GITHUB_USERNAME="chenxingqiang"
REGISTRY_URL="registry.cn-hangzhou.aliyuncs.com"
NAMESPACE="boltz"
IMAGE_NAME_INFERENCE="boltz-inference"
IMAGE_NAME_TRAINING="boltz-training"
VERSION=$(git describe --tags --always)

# 检查必要的环境变量
check_env_vars() {
    echo -e "${YELLOW}Checking environment variables...${NC}"
    
    if [ -z "$ALIYUN_ACCESS_KEY_ID" ] || [ -z "$ALIYUN_ACCESS_KEY_SECRET" ]; then
        echo -e "${RED}Error: ALIYUN_ACCESS_KEY_ID and ALIYUN_ACCESS_KEY_SECRET must be set${NC}"
        echo "Export them with:"
        echo "export ALIYUN_ACCESS_KEY_ID=your_key_id"
        echo "export ALIYUN_ACCESS_KEY_SECRET=your_key_secret"
        exit 1
    fi
    
    if [ -z "$ALIYUN_CLUSTER_ID" ]; then
        echo -e "${RED}Error: ALIYUN_CLUSTER_ID must be set${NC}"
        echo "Export it with:"
        echo "export ALIYUN_CLUSTER_ID=your_cluster_id"
        exit 1
    fi
    
    echo -e "${GREEN}Environment variables check passed${NC}"
}

# 安装必要的工具
install_tools() {
    echo -e "${YELLOW}Installing required tools...${NC}"
    
    # 安装阿里云CLI
    if ! command -v aliyun &> /dev/null; then
        echo "Installing Aliyun CLI..."
        curl -o aliyun-cli-linux-latest-amd64.tgz https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
        tar xzvf aliyun-cli-linux-latest-amd64.tgz
        sudo mv aliyun /usr/local/bin/
        rm aliyun-cli-linux-latest-amd64.tgz
    fi
    
    # 安装kubectl（如果没有）
    if ! command -v kubectl &> /dev/null; then
        echo "Installing kubectl..."
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        chmod +x kubectl
        sudo mv kubectl /usr/local/bin/
    fi
    
    echo -e "${GREEN}Tools installation completed${NC}"
}

# 配置阿里云和Kubernetes
configure_aliyun() {
    echo -e "${YELLOW}Configuring Aliyun and Kubernetes...${NC}"
    
    # 配置阿里云凭证
    aliyun configure set \
        --profile default \
        --mode AK \
        --region cn-hangzhou \
        --access-key-id $ALIYUN_ACCESS_KEY_ID \
        --access-key-secret $ALIYUN_ACCESS_KEY_SECRET
    
    # 获取K8s配置
    mkdir -p ~/.kube
    aliyun cs GET /k8s/$ALIYUN_CLUSTER_ID/user_config | jq -r .config > ~/.kube/config
    
    echo -e "${GREEN}Aliyun and Kubernetes configured${NC}"
}

# 构建和推送Docker镜像
build_and_push_images() {
    echo -e "${YELLOW}Building and pushing Docker images...${NC}"
    
    # 登录到阿里云容器镜像服务
    docker login --username=$ALIYUN_ACCESS_KEY_ID --password=$ALIYUN_ACCESS_KEY_SECRET $REGISTRY_URL
    
    # 构建和推送推理服务镜像
    echo "Building inference service image..."
    docker build -t $REGISTRY_URL/$NAMESPACE/$IMAGE_NAME_INFERENCE:$VERSION -f docker/inference.Dockerfile .
    docker push $REGISTRY_URL/$NAMESPACE/$IMAGE_NAME_INFERENCE:$VERSION
    docker tag $REGISTRY_URL/$NAMESPACE/$IMAGE_NAME_INFERENCE:$VERSION $REGISTRY_URL/$NAMESPACE/$IMAGE_NAME_INFERENCE:latest
    docker push $REGISTRY_URL/$NAMESPACE/$IMAGE_NAME_INFERENCE:latest
    
    # 构建和推送训练服务镜像
    echo "Building training service image..."
    docker build -t $REGISTRY_URL/$NAMESPACE/$IMAGE_NAME_TRAINING:$VERSION -f docker/training.Dockerfile .
    docker push $REGISTRY_URL/$NAMESPACE/$IMAGE_NAME_TRAINING:$VERSION
    docker tag $REGISTRY_URL/$NAMESPACE/$IMAGE_NAME_TRAINING:$VERSION $REGISTRY_URL/$NAMESPACE/$IMAGE_NAME_TRAINING:latest
    docker push $REGISTRY_URL/$NAMESPACE/$IMAGE_NAME_TRAINING:latest
    
    echo -e "${GREEN}Images built and pushed successfully${NC}"
}

# 更新Kubernetes配置
update_k8s_configs() {
    echo -e "${YELLOW}Updating Kubernetes configurations...${NC}"
    
    # 替换镜像标签
    sed -i.bak "s|image:.*boltz-inference.*|image: $REGISTRY_URL/$NAMESPACE/$IMAGE_NAME_INFERENCE:$VERSION|g" k8s/inference-deployment.yaml
    sed -i.bak "s|image:.*boltz-training.*|image: $REGISTRY_URL/$NAMESPACE/$IMAGE_NAME_TRAINING:$VERSION|g" k8s/training-deployment.yaml
    
    echo -e "${GREEN}Kubernetes configurations updated${NC}"
}

# 部署到Kubernetes
deploy_to_k8s() {
    echo -e "${YELLOW}Deploying to Kubernetes...${NC}"
    
    # 创建命名空间（如果不存在）
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # 部署服务
    kubectl apply -f k8s/inference-deployment.yaml -n $NAMESPACE
    kubectl apply -f k8s/training-deployment.yaml -n $NAMESPACE
    
    # 等待部署完成
    kubectl rollout status deployment/boltz-inference -n $NAMESPACE
    kubectl rollout status deployment/boltz-training -n $NAMESPACE
    
    echo -e "${GREEN}Deployment completed successfully${NC}"
}

# 验证部署
verify_deployment() {
    echo -e "${YELLOW}Verifying deployment...${NC}"
    
    # 检查Pod状态
    kubectl get pods -n $NAMESPACE -l app=boltz-inference
    kubectl get pods -n $NAMESPACE -l app=boltz-training
    
    # 检查服务状态
    kubectl get services -n $NAMESPACE
    
    echo -e "${GREEN}Verification completed${NC}"
}

# 主函数
main() {
    echo -e "${YELLOW}Starting deployment process...${NC}"
    
    check_env_vars
    install_tools
    configure_aliyun
    build_and_push_images
    update_k8s_configs
    deploy_to_k8s
    verify_deployment
    
    echo -e "${GREEN}Deployment completed successfully!${NC}"
    echo "You can access your services at:"
    kubectl get services -n $NAMESPACE -o wide
}

# 执行主函数
main
