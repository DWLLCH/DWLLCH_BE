from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Policy
from .serializers import PolicyListSerializer, PolicyDetailSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def policy_list(request):
    queryset = Policy.objects.all().order_by("-created_at")

    category = request.query_params.get("category")
    if category:
        queryset = queryset.filter(category=category)

    keyword = request.query_params.get("keyword")
    if keyword:
        queryset = queryset.filter(title__icontains=keyword)

    serializer = PolicyListSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def policy_detail(request, policy_id):
    try:
        policy = Policy.objects.get(id=policy_id)
    except Policy.DoesNotExist:
        return Response(
            {"detail": "정책을 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = PolicyDetailSerializer(policy)
    return Response(serializer.data, status=status.HTTP_200_OK)