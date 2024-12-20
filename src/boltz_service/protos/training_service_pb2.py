# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: training_service.proto
# Protobuf Python Version: 5.28.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    28,
    1,
    '',
    'training_service.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


import boltz_service.protos.common_pb2 as common__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x16training_service.proto\x12\x05\x62oltz\x1a\x0c\x63ommon.proto\"\xa5\x02\n\x0fTrainingRequest\x12\x0e\n\x06job_id\x18\x01 \x01(\t\x12\x13\n\x0b\x63onfig_path\x18\x02 \x01(\t\x12\x0c\n\x04\x61rgs\x18\x03 \x03(\t\x12\x10\n\x08num_gpus\x18\x04 \x01(\x05\x12\x12\n\noutput_dir\x18\x05 \x01(\t\x12\x0e\n\x06resume\x18\x06 \x01(\x08\x12\x12\n\ncheckpoint\x18\x07 \x01(\t\x12\x17\n\x0f\x65xperiment_name\x18\x08 \x01(\t\x12\x44\n\x0fhyperparameters\x18\t \x03(\x0b\x32+.boltz.TrainingRequest.HyperparametersEntry\x1a\x36\n\x14HyperparametersEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"b\n\x10TrainingResponse\x12\x0e\n\x06job_id\x18\x01 \x01(\t\x12\x0e\n\x06status\x18\x02 \x01(\t\x12\x17\n\x0f\x63heckpoint_path\x18\x03 \x01(\t\x12\x15\n\rerror_message\x18\x04 \x01(\t\"\x99\x01\n\x19TrainingJobStatusResponse\x12&\n\x04\x62\x61se\x18\x01 \x01(\x0b\x32\x18.boltz.JobStatusResponse\x12\x15\n\rcurrent_epoch\x18\x02 \x01(\x02\x12\x10\n\x08val_loss\x18\x03 \x01(\x02\x12\x12\n\ntrain_loss\x18\x04 \x01(\x02\x12\x17\n\x0f\x63heckpoint_path\x18\x05 \x01(\t\"I\n\x12\x45xportModelRequest\x12\x0e\n\x06job_id\x18\x01 \x01(\t\x12\x13\n\x0boutput_path\x18\x02 \x01(\t\x12\x0e\n\x06\x66ormat\x18\x03 \x01(\t\"`\n\x13\x45xportModelResponse\x12\x0e\n\x06job_id\x18\x01 \x01(\t\x12\x0e\n\x06status\x18\x02 \x01(\t\x12\x12\n\nmodel_path\x18\x03 \x01(\t\x12\x15\n\rerror_message\x18\x04 \x01(\t2\xac\x02\n\x0fTrainingService\x12\x42\n\rStartTraining\x12\x16.boltz.TrainingRequest\x1a\x17.boltz.TrainingResponse\"\x00\x12K\n\x0cGetJobStatus\x12\x17.boltz.JobStatusRequest\x1a .boltz.TrainingJobStatusResponse\"\x00\x12@\n\tCancelJob\x12\x17.boltz.CancelJobRequest\x1a\x18.boltz.CancelJobResponse\"\x00\x12\x46\n\x0b\x45xportModel\x12\x19.boltz.ExportModelRequest\x1a\x1a.boltz.ExportModelResponse\"\x00\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'training_service_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_TRAININGREQUEST_HYPERPARAMETERSENTRY']._loaded_options = None
  _globals['_TRAININGREQUEST_HYPERPARAMETERSENTRY']._serialized_options = b'8\001'
  _globals['_TRAININGREQUEST']._serialized_start=48
  _globals['_TRAININGREQUEST']._serialized_end=341
  _globals['_TRAININGREQUEST_HYPERPARAMETERSENTRY']._serialized_start=287
  _globals['_TRAININGREQUEST_HYPERPARAMETERSENTRY']._serialized_end=341
  _globals['_TRAININGRESPONSE']._serialized_start=343
  _globals['_TRAININGRESPONSE']._serialized_end=441
  _globals['_TRAININGJOBSTATUSRESPONSE']._serialized_start=444
  _globals['_TRAININGJOBSTATUSRESPONSE']._serialized_end=597
  _globals['_EXPORTMODELREQUEST']._serialized_start=599
  _globals['_EXPORTMODELREQUEST']._serialized_end=672
  _globals['_EXPORTMODELRESPONSE']._serialized_start=674
  _globals['_EXPORTMODELRESPONSE']._serialized_end=770
  _globals['_TRAININGSERVICE']._serialized_start=773
  _globals['_TRAININGSERVICE']._serialized_end=1073
# @@protoc_insertion_point(module_scope)
