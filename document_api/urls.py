from django.urls import path
from .views import ScreenDocumentView, AdminStatsView, DemoSamplesView, index_view

urlpatterns = [
    path('', index_view, name='index'),
    path('api/screen/', ScreenDocumentView.as_view(), name='api_screen'),
    path('api/stats/', AdminStatsView.as_view(), name='api_stats'),
    path('api/demo-samples/', DemoSamplesView.as_view(), name='api_demo_samples'),
]
