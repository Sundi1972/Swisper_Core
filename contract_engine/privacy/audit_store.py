import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import gzip
import io

logger = logging.getLogger(__name__)

class S3AuditStore:
    """S3-based storage for auditable artifacts and GDPR compliance"""
    
    def __init__(self):
        self.bucket_name = os.getenv("SWISPER_AUDIT_BUCKET", "swisper-audit-artifacts")
        self.region = os.getenv("AWS_REGION", "eu-central-1")
        self.s3_client = None
        self._initialize_s3_client()
    
    def _initialize_s3_client(self):
        """Initialize S3 client with Switzerland/EU configuration"""
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
            )
            
            self._ensure_audit_bucket()
            
            logger.info(f"S3 audit store initialized: {self.bucket_name}")
            
        except NoCredentialsError:
            logger.warning("AWS credentials not found. S3 audit store disabled.")
            self.s3_client = None
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None
    
    def _ensure_audit_bucket(self):
        """Ensure audit bucket exists with proper configuration"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                try:
                    if self.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    logger.info(f"Created audit bucket: {self.bucket_name}")
                except Exception as create_error:
                    logger.error(f"Failed to create audit bucket: {create_error}")
                    raise
            else:
                raise
    
    def store_chat_artifact(self, session_id: str, user_id: str, chat_history: List[Dict[str, Any]]) -> bool:
        """Store complete chat history for audit trail"""
        try:
            if not self.s3_client:
                return False
            
            timestamp = datetime.utcnow()
            artifact = {
                "artifact_type": "chat_history",
                "session_id": session_id,
                "user_id": user_id,
                "timestamp": timestamp.isoformat(),
                "chat_history": chat_history,
                "message_count": len(chat_history),
                "retention_policy": "7_years"
            }
            
            compressed_data = self._compress_artifact(artifact)
            s3_key = f"audit/chat/{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/{session_id}_{timestamp.strftime('%H%M%S')}.json.gz"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=compressed_data,
                ContentType='application/gzip',
                Metadata={
                    'session_id': session_id,
                    'user_id': user_id,
                    'artifact_type': 'chat_history'
                }
            )
            
            logger.info(f"Stored chat artifact: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store chat artifact: {e}")
            return False
    
    def store_fsm_artifact(self, session_id: str, user_id: str, fsm_logs: List[Dict[str, Any]]) -> bool:
        """Store FSM state transition logs for audit trail"""
        try:
            if not self.s3_client:
                return False
            
            timestamp = datetime.utcnow()
            artifact = {
                "artifact_type": "fsm_logs",
                "session_id": session_id,
                "user_id": user_id,
                "timestamp": timestamp.isoformat(),
                "fsm_logs": fsm_logs,
                "transition_count": len(fsm_logs),
                "retention_policy": "7_years"
            }
            
            compressed_data = self._compress_artifact(artifact)
            s3_key = f"audit/fsm/{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/{session_id}_{timestamp.strftime('%H%M%S')}.json.gz"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=compressed_data,
                ContentType='application/gzip',
                Metadata={
                    'session_id': session_id,
                    'user_id': user_id,
                    'artifact_type': 'fsm_logs'
                }
            )
            
            logger.info(f"Stored FSM artifact: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store FSM artifact: {e}")
            return False
    
    def store_contract_artifact(self, session_id: str, user_id: str, contract_data: Dict[str, Any]) -> bool:
        """Store contract JSON for audit trail"""
        try:
            if not self.s3_client:
                return False
            
            timestamp = datetime.utcnow()
            artifact = {
                "artifact_type": "contract_json",
                "session_id": session_id,
                "user_id": user_id,
                "timestamp": timestamp.isoformat(),
                "contract_data": contract_data,
                "retention_policy": "7_years"
            }
            
            compressed_data = self._compress_artifact(artifact)
            s3_key = f"audit/contracts/{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/{session_id}_{timestamp.strftime('%H%M%S')}.json.gz"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=compressed_data,
                ContentType='application/gzip',
                Metadata={
                    'session_id': session_id,
                    'user_id': user_id,
                    'artifact_type': 'contract_json'
                }
            )
            
            logger.info(f"Stored contract artifact: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store contract artifact: {e}")
            return False
    
    def get_user_artifacts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all artifacts for a user (GDPR compliance)"""
        try:
            if not self.s3_client:
                return []
            
            artifacts = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix="audit/"):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        try:
                            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=obj['Key'])
                            metadata = response.get('Metadata', {})
                            
                            if metadata.get('user_id') == user_id:
                                last_modified = obj['LastModified']
                                if hasattr(last_modified, 'isoformat'):
                                    last_modified_str = last_modified.isoformat()
                                else:
                                    last_modified_str = str(last_modified)
                                
                                artifacts.append({
                                    "key": obj['Key'],
                                    "size": obj['Size'],
                                    "last_modified": last_modified_str,
                                    "artifact_type": metadata.get('artifact_type'),
                                    "session_id": metadata.get('session_id')
                                })
                        except Exception as e:
                            logger.warning(f"Failed to get metadata for {obj['Key']}: {e}")
            
            return artifacts
            
        except Exception as e:
            logger.error(f"Failed to get user artifacts: {e}")
            return []
    
    def delete_user_artifacts(self, user_id: str) -> bool:
        """Delete all artifacts for a user (GDPR right to be forgotten)"""
        try:
            if not self.s3_client:
                return True
            
            user_artifacts = self.get_user_artifacts(user_id)
            
            if not user_artifacts:
                return True
            
            delete_objects = [{'Key': artifact['key']} for artifact in user_artifacts]
            
            response = self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': delete_objects}
            )
            
            deleted_count = len(response.get('Deleted', []))
            logger.info(f"Deleted {deleted_count} artifacts for user {user_id}")
            
            return deleted_count > 0 or len(delete_objects) == 0
            
        except Exception as e:
            logger.error(f"Failed to delete user artifacts: {e}")
            return False
    
    def _compress_artifact(self, artifact: Dict[str, Any]) -> bytes:
        """Compress artifact data for efficient storage"""
        json_data = json.dumps(artifact, indent=None, separators=(',', ':'))
        
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as gz_file:
            gz_file.write(json_data.encode('utf-8'))
        
        return buffer.getvalue()

audit_store = S3AuditStore()
