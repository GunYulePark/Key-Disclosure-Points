"""Pure local contract tests for TASK 01. No HTTP/SQL client or cloud writes."""
import hashlib, re, uuid
from workspace_inventory import official
NAMESPACE=uuid.UUID('b543ee53-3093-5b42-900c-e6ed0f20ae62')
def document_id(source_url,legacy_id):
 if not official(source_url):raise ValueError('official_https_source_required')
 if not legacy_id:raise ValueError('legacy_id_required')
 return str(uuid.uuid5(NAMESPACE,source_url+'\n'+legacy_id))
def version_id(document,sha256):
 uuid.UUID(document)
 if not re.fullmatch('[0-9a-f]{64}',sha256):raise ValueError('invalid_sha256')
 return str(uuid.uuid5(NAMESPACE,document+'\n'+sha256))
def object_path(document,sha256,extension):
 if extension not in {'pdf','xml','html','zip','hwp','jpeg','png'}:raise ValueError('unsupported_extension')
 return f'originals/{document}/{version_id(document,sha256)}/{sha256}.{extension}'
def verify_original(raw,expected_sha256):
 if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('original_hash_mismatch')
def update_revision(current,expected):
 if type(current)!=int or current<0 or type(expected)!=int or expected!=current:raise ValueError('revision_conflict')
 return current+1
