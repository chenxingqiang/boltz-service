import grpc
import os
from boltz_service.protos import inference_service_pb2_grpc
from boltz_service.protos import inference_service_pb2
from boltz_service.protos import common_pb2

def test_inference():
    # Create a gRPC channel
    channel = grpc.insecure_channel('localhost:50051')
    
    # Create a stub (client)
    stub = inference_service_pb2_grpc.InferenceServiceStub(channel)
    
    # Create a request
    request = inference_service_pb2.PredictionRequest(
        job_id="test_job_1",
        sequence="MKFLVLLFNILCLFPVLAADNHGVGPQGASGVDPITFDINSNQTGPAFLTAVEMAGVKYLQVQHGSNVNIHRLVEGNVVIWENASTPLYTGAIVTNNDGPYMAYVEVLGDPNLQFFIKSGDAWVTLSEHEYLAKLQEIRQAVHIESVFSLNMAFQLENNKYEVETHAKNGANMVTFIPRNGHICKMVYHKNVRIYKATGPGPLIYLNNDTKNLLQTATATVRNITVPDLYVLVEDEDLVVQNPNNPTIHVGNTGYQGGDVVHEANGTSLRDLHIKDGDNFYIYLMDGAHVPDEWQVRASDPGLPGAYRFVGETIKNNHKEFVLPPGEYILVLHFECHKDGKFYPSPGKYTMDGKEVKLDYQNVEGVWKIINDATQVWGGGENL",
        recycling_steps=3,
        sampling_steps=20,
        diffusion_samples=1,
        output_format="pdb",
        model_version="latest"
    )
    
    try:
        # Make the call
        response = stub.PredictStructure(request)
        print("Prediction request successful!")
        print(f"Job ID: {response.job_id}")
        print(f"Status: {response.status}")
        print(f"Result Path: {response.result_path}")
        return True
    except grpc.RpcError as e:
        print(f"RPC failed: {e.code()}")
        print(f"Details: {e.details()}")
        return False

if __name__ == "__main__":
    # Test inference
    success = test_inference()
    if success:
        print("All tests passed!")
    else:
        print("Tests failed!")
