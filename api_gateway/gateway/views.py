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
        
    upstream_url = settings.SERVICE_MAP[service]
    
    # Reconstruct the target URL
    target_url = f"{upstream_url}/api/v1/{service}/{path}"
    
    if request.META.get('QUERY_STRING'):
        target_url += f"?{request.META['QUERY_STRING']}"
        
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ['host', 'content-length']}
    
    try:
        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.body,
            stream=True,
            timeout=30,
        )
        
        # Build HttpResponse from the upstream response
        proxy_response = HttpResponse(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('content-type', 'application/json')
        )
        
        # Copy headers from upstream back to client
        for key, value in response.headers.items():
            if key.lower() not in ['transfer-encoding', 'content-encoding', 'connection']:
                proxy_response[key] = value
                
        return proxy_response
        
    except requests.exceptions.Timeout:
        return JsonResponse({'success': False, 'message': 'Downstream service timeout'}, status=504)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'success': False, 'message': f'Gateway Error: {str(e)}'}, status=502)
