"""Tests for Gateway proxy routes."""
import pytest
from django.urls import reverse
from unittest.mock import patch, Mock
import json
from django.test import Client

@pytest.fixture
def client():
    return Client()

class TestGateway:
    @patch('gateway.views.requests.request')
    def test_proxy_forwards_request(self, mock_request, client):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"success": true}'
        mock_response.headers = {'content-type': 'application/json'}
        mock_request.return_value = mock_response
        
        response = client.get('/api/v1/users/?test=1')
        
        # Check gateway return
        assert response.status_code == 200
        assert json.loads(response.content) == {"success": True}
        
        # Assert parameters passed to requests correctly
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs['method'] == 'GET'
        assert 'http://localhost:8001/api/v1/users/' in kwargs['url']
        
    def test_missing_service(self, client):
        response = client.get('/api/v1/unknownservice/test')
        assert response.status_code == 404
        assert json.loads(response.content) == {'success': False, 'message': 'Service not found'}
