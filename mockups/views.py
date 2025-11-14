from rest_framework.views import APIView  # type: ignore[import]
from rest_framework.response import Response  # type: ignore[import]
from rest_framework import status  # type: ignore[import]
from django.shortcuts import get_object_or_404
try:
    from rest_framework.generics import ListAPIView  # type: ignore[import]
except ImportError:  # pragma: no cover
    class ListAPIView:  # type: ignore[misc]
        pass
from .models import GenerationTask, GeneratedImage, Mockup
from .serializers import GeneratedImageSerializer, MockupSerializer
from .tasks import generate_mockup_task
import uuid


class GenerateMockupView(APIView):
    def post(self, request):
        data = request.data
        text = data.get('text', '')
        if not text:
            return Response({
                'error': 'text field is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        font = data.get('font', None)
        text_color = data.get('text_color', '#000000')
        shirt_colors = data.get('shirt_color', None)  # optional list
        
        # If no shirt_colors provided, default to all 4 colors
        if shirt_colors is None:
            from .tasks import DEFAULT_SHIRT_COLORS
            shirt_colors = DEFAULT_SHIRT_COLORS

        # create GenerationTask record
        task_uuid = uuid.uuid4()
        GenerationTask.objects.create(task_id=task_uuid, status='PENDING')

        # call celery async task with correct parameters
        generate_mockup_task.delay(
            str(task_uuid),
            text,
            font_name=font,
            text_color=text_color,
            shirt_colors=shirt_colors
        )

        return Response({
            'task_id': str(task_uuid),
            'status': 'PENDING',
            'message': 'Image generation started'
        }, status=status.HTTP_202_ACCEPTED)


class TaskStatusView(APIView):
    def get(self, request, task_id):
        gen_task = get_object_or_404(GenerationTask, task_id=task_id)
        data = {
            'task_id': str(gen_task.task_id),
            'status': gen_task.status,
            'results': []
        }
        if gen_task.mockup:
            images = gen_task.mockup.images.all()
            serializer = GeneratedImageSerializer(images, many=True, context={'request': request})
            data['results'] = serializer.data
        return Response(data)


class MockupListView(ListAPIView):
    queryset = Mockup.objects.prefetch_related('images').all().order_by('-created_at')
    serializer_class = MockupSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
