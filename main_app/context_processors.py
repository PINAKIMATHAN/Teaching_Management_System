from .models import Notice

def notice_count(request):
    count = Notice.objects.count()
    return {'notice_count': count}