from rest_framework import serializers
from .models import Mockup, GeneratedImage, GenerationTask

class GeneratedImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedImage
        fields = ['image_url', 'created_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

class MockupSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Mockup
        fields = ['id', 'text', 'image_url', 'font', 'text_color', 'shirt_color', 'created_at']

    def get_image_url(self, obj):
        # Return the first image URL for the mockup (as per spec)
        first_image = obj.images.first()
        if first_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None

class GenerationTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenerationTask
        fields = ['task_id', 'status', 'created_at']
