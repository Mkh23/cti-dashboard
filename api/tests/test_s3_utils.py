"""Tests for S3 utility functions."""
import pytest
from unittest.mock import patch, MagicMock
from app.s3_utils import generate_presigned_url, get_s3_client


def test_generate_presigned_url_success():
    """Test successful presigned URL generation."""
    with patch('app.s3_utils.get_s3_client') as mock_client:
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://example.com/signed-url"
        mock_client.return_value = mock_s3
        
        url = generate_presigned_url("test-bucket", "test-key.jpg")
        
        assert url == "https://example.com/signed-url"
        mock_s3.generate_presigned_url.assert_called_once()


def test_generate_presigned_url_with_custom_expiration():
    """Test presigned URL generation with custom expiration."""
    with patch('app.s3_utils.get_s3_client') as mock_client:
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://example.com/signed-url"
        mock_client.return_value = mock_s3
        
        url = generate_presigned_url("test-bucket", "test-key.jpg", expiration=7200)
        
        assert url == "https://example.com/signed-url"
        call_args = mock_s3.generate_presigned_url.call_args
        assert call_args[1]["ExpiresIn"] == 7200


def test_generate_presigned_url_client_error():
    """Test presigned URL generation handles client errors gracefully."""
    with patch('app.s3_utils.get_s3_client') as mock_client:
        from botocore.exceptions import ClientError
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket"}}, "generate_presigned_url"
        )
        mock_client.return_value = mock_s3
        
        url = generate_presigned_url("nonexistent-bucket", "test-key.jpg")
        
        assert url is None


def test_generate_presigned_url_no_credentials():
    """Test presigned URL generation when AWS credentials are not configured."""
    with patch('app.s3_utils.get_s3_client') as mock_client:
        mock_client.side_effect = Exception("No credentials found")
        
        url = generate_presigned_url("test-bucket", "test-key.jpg")
        
        assert url is None


def test_get_s3_client_with_profile():
    """Test S3 client creation with AWS profile."""
    with patch.dict('os.environ', {'AWS_PROFILE': 'test-profile', 'AWS_REGION': 'us-east-1'}):
        with patch('app.s3_utils.boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_session.return_value.client.return_value = mock_client
            
            client = get_s3_client()
            
            mock_session.assert_called_once_with(profile_name='test-profile', region_name='us-east-1')
            assert client == mock_client


def test_get_s3_client_without_profile():
    """Test S3 client creation without AWS profile."""
    with patch.dict('os.environ', {}, clear=True):
        with patch('app.s3_utils.os.environ.get') as mock_get:
            mock_get.side_effect = lambda key, default=None: default if key in ['CTI_AWS_PROFILE', 'AWS_PROFILE'] else 'ca-central-1'
            with patch('app.s3_utils.boto3.client') as mock_client:
                mock_s3 = MagicMock()
                mock_client.return_value = mock_s3
                
                client = get_s3_client()
                
                mock_client.assert_called_once_with('s3', region_name='ca-central-1')
                assert client == mock_s3
