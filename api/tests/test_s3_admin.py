from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError


def test_s3_admin_list_objects(client):
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "raw/a.txt", "Size": 12}],
        "IsTruncated": False,
        "KeyCount": 1,
    }
    with patch("app.routers.s3_admin.get_s3_client", return_value=mock_s3):
        response = client.get("/admin/s3/list", params={"prefix": "raw/", "max_keys": 1})

    assert response.status_code == 200
    data = response.json()
    assert data["bucket"]
    assert data["items"][0]["key"] == "raw/a.txt"


def test_s3_admin_list_objects_error(client):
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.side_effect = ClientError(
        {"Error": {"Message": "AccessDenied"}}, "list_objects_v2"
    )
    with patch("app.routers.s3_admin.get_s3_client", return_value=mock_s3):
        response = client.get("/admin/s3/list", params={"prefix": "raw/"})

    assert response.status_code == 400


def test_s3_admin_presign(client):
    with patch("app.routers.s3_admin.generate_presigned_url", return_value="https://example.com/url"):
        response = client.get("/admin/s3/presign", params={"key": "raw/a.txt", "expires": 120})

    assert response.status_code == 200
    assert response.json()["url"] == "https://example.com/url"


def test_s3_admin_presign_failure(client):
    with patch("app.routers.s3_admin.generate_presigned_url", return_value=None):
        response = client.get("/admin/s3/presign", params={"key": "raw/a.txt"})

    assert response.status_code == 400


def test_s3_admin_upload(client):
    mock_s3 = MagicMock()
    with patch("app.routers.s3_admin.get_s3_client", return_value=mock_s3):
        response = client.post(
            "/admin/s3/upload",
            params={"key": "raw/a.txt"},
            files={"file": ("a.txt", b"hello")},
        )

    assert response.status_code == 200
    mock_s3.upload_fileobj.assert_called_once()


def test_s3_admin_upload_error(client):
    mock_s3 = MagicMock()
    mock_s3.upload_fileobj.side_effect = ClientError(
        {"Error": {"Message": "AccessDenied"}}, "upload_fileobj"
    )
    with patch("app.routers.s3_admin.get_s3_client", return_value=mock_s3):
        response = client.post(
            "/admin/s3/upload",
            params={"key": "raw/a.txt"},
            files={"file": ("a.txt", b"hello")},
        )

    assert response.status_code == 400


def test_s3_admin_delete_object(client):
    mock_s3 = MagicMock()
    with patch("app.routers.s3_admin.get_s3_client", return_value=mock_s3):
        response = client.delete("/admin/s3/object", params={"key": "raw/a.txt"})

    assert response.status_code == 200
    _, kwargs = mock_s3.delete_object.call_args
    assert kwargs["Key"] == "raw/a.txt"
