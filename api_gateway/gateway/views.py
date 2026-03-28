import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def gateway_proxy(request, service, path):
    """
    Proxy requests from the Gateway to the respective Microservices.
    Example: 
    GET /api/v1/users/login/ -> mapped to USER_SERVICE_URL/api/v1/users/login/
    """
    if service not in settings.SERVICE_MAP:
        return JsonResponse({'success': False, 'message': 'Service not found'}, status=404)
        
    upstream_url = settings.SERVICE_MAP[service].rstrip('/')
    if not upstream_url.startswith(('http://', 'https://')):
        upstream_url = f"https://{upstream_url}"
    
    # Reconstruct the target URL
    service_prefix = f"api/v1/{service}".rstrip('/')
    target_url = f"{upstream_url}/{service_prefix}/"
    if path:
        # path might already have a trailing slash from the regex
        target_url = f"{upstream_url}/{service_prefix}/{path.lstrip('/')}"
    
    if request.META.get('QUERY_STRING'):
        target_url = f"{target_url.rstrip('/')}/?{request.META['QUERY_STRING']}"

    # Strip headers that must not be forwarded to upstream.
    # Crucially, drop 'accept-encoding' so that `requests` negotiates only
    # gzip/deflate (which it decompresses automatically).  If we forward
    # Postman's "br" (Brotli) preference the upstream may return Brotli
    # data that `requests` cannot decompress, resulting in binary garbage.
    STRIP_REQUEST_HEADERS = {'host', 'content-length', 'accept-encoding'}
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in STRIP_REQUEST_HEADERS
    }
    
    try:
        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.body,
            stream=False,
            timeout=60,  # Increased timeout for Free Tier wake-up
        )
        
        # `requests` transparently decompresses gzip/deflate, so
        # response.content is already plain text at this point.
        # Build HttpResponse from the upstream response
        proxy_response = HttpResponse(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('content-type', 'application/json')
        )
        
        # Copy headers from upstream back to client
        for key, value in response.headers.items():
            # Skip architectural headers that Django/Gunicorn should handle or that change after proxying
            if key.lower() not in [
                'transfer-encoding', 
                'content-encoding', 
                'connection', 
                'content-length',
                'server'
            ]:
                proxy_response[key] = value
                
        return proxy_response
        
    except requests.exceptions.Timeout:
        return JsonResponse({'success': False, 'message': 'Downstream service timeout'}, status=504)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'success': False, 'message': f'Gateway Error: {str(e)}'}, status=502)
