"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 0, '', 'profile_api/v1/profile.proto')
_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x1cprofile_api/v1/profile.proto\x12\x0eprofile_api.v1"\x0f\n\rHealthRequest"\x1c\n\x0eHealthResponse\x12\n\n\x02ok\x18\x01 \x01(\x08"\xd3\x01\n\x14CreateProfileRequest\x12\x13\n\x0btelegram_id\x18\x01 \x01(\x03\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x0b\n\x03age\x18\x03 \x01(\x05\x12\x0c\n\x04city\x18\x04 \x01(\t\x12\x0b\n\x03bio\x18\x05 \x01(\t\x12&\n\x06gender\x18\x06 \x01(\x0e2\x16.profile_api.v1.Gender\x12\x15\n\x08latitude\x18\x07 \x01(\x01H\x00\x88\x01\x01\x12\x16\n\tlongitude\x18\x08 \x01(\x01H\x01\x88\x01\x01B\x0b\n\t_latitudeB\x0c\n\n_longitude"+\n\x15CreateProfileResponse\x12\x12\n\nprofile_id\x18\x01 \x01(\x03"(\n\x11GetProfileRequest\x12\x13\n\x0btelegram_id\x18\x01 \x01(\x03"\x8a\x02\n\x12GetProfileResponse\x12\r\n\x05found\x18\x01 \x01(\x08\x12\x12\n\nprofile_id\x18\x02 \x01(\x03\x12\x0c\n\x04name\x18\x03 \x01(\t\x12\x0b\n\x03age\x18\x04 \x01(\x05\x12\x0c\n\x04city\x18\x05 \x01(\t\x12\x0b\n\x03bio\x18\x06 \x01(\t\x12&\n\x06gender\x18\x07 \x01(\x0e2\x16.profile_api.v1.Gender\x12)\n\x06photos\x18\x08 \x03(\x0b2\x19.profile_api.v1.PhotoInfo\x12\x15\n\x08latitude\x18\t \x01(\x01H\x00\x88\x01\x01\x12\x16\n\tlongitude\x18\n \x01(\x01H\x01\x88\x01\x01B\x0b\n\t_latitudeB\x0c\n\n_longitude"0\n\tPhotoInfo\x12\x10\n\x08photo_id\x18\x01 \x01(\x03\x12\x11\n\tis_active\x18\x02 \x01(\x08"a\n\x14UpdateProfileRequest\x12\x13\n\x0btelegram_id\x18\x01 \x01(\x03\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x0b\n\x03age\x18\x03 \x01(\x05\x12\x0c\n\x04city\x18\x04 \x01(\t\x12\x0b\n\x03bio\x18\x05 \x01(\t"(\n\x15UpdateProfileResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08"I\n\rSetGeoRequest\x12\x13\n\x0btelegram_id\x18\x01 \x01(\x03\x12\x10\n\x08latitude\x18\x02 \x01(\x01\x12\x11\n\tlongitude\x18\x03 \x01(\x01"!\n\x0eSetGeoResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08"M\n\x12UploadPhotoRequest\x12\x13\n\x0btelegram_id\x18\x01 \x01(\x03\x12\x0c\n\x04data\x18\x02 \x01(\x0c\x12\x14\n\x0ccontent_type\x18\x03 \x01(\t":\n\x13UploadPhotoResponse\x12\x10\n\x08photo_id\x18\x01 \x01(\x03\x12\x11\n\tminio_key\x18\x02 \x01(\t";\n\x12DeletePhotoRequest\x12\x13\n\x0btelegram_id\x18\x01 \x01(\x03\x12\x10\n\x08photo_id\x18\x02 \x01(\x03"&\n\x13DeletePhotoResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08"*\n\x16GetPresignedUrlRequest\x12\x10\n\x08photo_id\x18\x01 \x01(\x03"&\n\x17GetPresignedUrlResponse\x12\x0b\n\x03url\x18\x01 \x01(\t*D\n\x06Gender\x12\x16\n\x12GENDER_UNSPECIFIED\x10\x00\x12\x0f\n\x0bGENDER_MALE\x10\x01\x12\x11\n\rGENDER_FEMALE\x10\x022\xc7\x05\n\x0eProfileService\x12G\n\x06Health\x12\x1d.profile_api.v1.HealthRequest\x1a\x1e.profile_api.v1.HealthResponse\x12\\\n\rCreateProfile\x12$.profile_api.v1.CreateProfileRequest\x1a%.profile_api.v1.CreateProfileResponse\x12S\n\nGetProfile\x12!.profile_api.v1.GetProfileRequest\x1a".profile_api.v1.GetProfileResponse\x12\\\n\rUpdateProfile\x12$.profile_api.v1.UpdateProfileRequest\x1a%.profile_api.v1.UpdateProfileResponse\x12G\n\x06SetGeo\x12\x1d.profile_api.v1.SetGeoRequest\x1a\x1e.profile_api.v1.SetGeoResponse\x12V\n\x0bUploadPhoto\x12".profile_api.v1.UploadPhotoRequest\x1a#.profile_api.v1.UploadPhotoResponse\x12V\n\x0bDeletePhoto\x12".profile_api.v1.DeletePhotoRequest\x1a#.profile_api.v1.DeletePhotoResponse\x12b\n\x0fGetPresignedUrl\x12&.profile_api.v1.GetPresignedUrlRequest\x1a\'.profile_api.v1.GetPresignedUrlResponseb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'profile_api.v1.profile_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_GENDER']._serialized_start = 1290
    _globals['_GENDER']._serialized_end = 1358
    _globals['_HEALTHREQUEST']._serialized_start = 48
    _globals['_HEALTHREQUEST']._serialized_end = 63
    _globals['_HEALTHRESPONSE']._serialized_start = 65
    _globals['_HEALTHRESPONSE']._serialized_end = 93
    _globals['_CREATEPROFILEREQUEST']._serialized_start = 96
    _globals['_CREATEPROFILEREQUEST']._serialized_end = 307
    _globals['_CREATEPROFILERESPONSE']._serialized_start = 309
    _globals['_CREATEPROFILERESPONSE']._serialized_end = 352
    _globals['_GETPROFILEREQUEST']._serialized_start = 354
    _globals['_GETPROFILEREQUEST']._serialized_end = 394
    _globals['_GETPROFILERESPONSE']._serialized_start = 397
    _globals['_GETPROFILERESPONSE']._serialized_end = 663
    _globals['_PHOTOINFO']._serialized_start = 665
    _globals['_PHOTOINFO']._serialized_end = 713
    _globals['_UPDATEPROFILEREQUEST']._serialized_start = 715
    _globals['_UPDATEPROFILEREQUEST']._serialized_end = 812
    _globals['_UPDATEPROFILERESPONSE']._serialized_start = 814
    _globals['_UPDATEPROFILERESPONSE']._serialized_end = 854
    _globals['_SETGEOREQUEST']._serialized_start = 856
    _globals['_SETGEOREQUEST']._serialized_end = 929
    _globals['_SETGEORESPONSE']._serialized_start = 931
    _globals['_SETGEORESPONSE']._serialized_end = 964
    _globals['_UPLOADPHOTOREQUEST']._serialized_start = 966
    _globals['_UPLOADPHOTOREQUEST']._serialized_end = 1043
    _globals['_UPLOADPHOTORESPONSE']._serialized_start = 1045
    _globals['_UPLOADPHOTORESPONSE']._serialized_end = 1103
    _globals['_DELETEPHOTOREQUEST']._serialized_start = 1105
    _globals['_DELETEPHOTOREQUEST']._serialized_end = 1164
    _globals['_DELETEPHOTORESPONSE']._serialized_start = 1166
    _globals['_DELETEPHOTORESPONSE']._serialized_end = 1204
    _globals['_GETPRESIGNEDURLREQUEST']._serialized_start = 1206
    _globals['_GETPRESIGNEDURLREQUEST']._serialized_end = 1248
    _globals['_GETPRESIGNEDURLRESPONSE']._serialized_start = 1250
    _globals['_GETPRESIGNEDURLRESPONSE']._serialized_end = 1288
    _globals['_PROFILESERVICE']._serialized_start = 1361
    _globals['_PROFILESERVICE']._serialized_end = 2072