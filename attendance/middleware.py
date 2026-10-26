import logging, time
from django.http import HttpResponseForbidden
# from .permissions import role
class AuditMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        start=time.monotonic()
        if request.path.startswith('/upload/') and request.user.is_authenticated and (request.user)!='HR':
            response=HttpResponseForbidden('HR access required')
        else: response=self.get_response(request)
        logging.getLogger('audit').info('%s %s user=%s status=%s ms=%.1f',request.method,request.path,request.user.pk,response.status_code,(time.monotonic()-start)*1000)
        return response
