from django.db import models
import uuid

class Mockup(models.Model):
    text = models.TextField()
    font = models.CharField(max_length=100, blank=True, null=True)
    text_color = models.CharField(max_length=7, blank=True, null=True)  # e.g. #FFFFFF
    shirt_color = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mockup {self.id} - {self.text[:20]}"

class GeneratedImage(models.Model):
    mockup = models.ForeignKey(Mockup, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='mockups/')
    created_at = models.DateTimeField(auto_now_add=True)

class GenerationTask(models.Model):
    # نگهداری تسک برای query با task_id
    task_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    mockup = models.ForeignKey(Mockup, null=True, blank=True, on_delete=models.SET_NULL)
