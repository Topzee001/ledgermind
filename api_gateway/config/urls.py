"""API Gateway routing URLs.
Forwards all /api/v1/* requests to the appropriate microservice.
"""
from django.urls import path, re_path
from gateway.views import gateway_proxy

urlpatterns = [
    re_path(r'^api/v1/(?P<service>[a-zA-Z0-9_\-]+)/?(?P<path>.*)$', gateway_proxy, name='gateway_proxy'),
]
