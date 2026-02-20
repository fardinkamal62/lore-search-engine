from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model

from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
)
from .utils import AuthUtils, UserUtils

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Use AuthUtils for token generation
            token = AuthUtils.generate_user_token(user)

            return Response({
                'user': UserSerializer(user).data,
                'token': token.key,
                'message': 'Registration successful. You can now log in.'
            }, status=status.HTTP_201_CREATED)

        return Response({
            'errors': serializer.errors,
            'message': 'Registration failed. Please check the provided data.'
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Use AuthUtils for token generation
            token = AuthUtils.generate_user_token(user)

            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)

        return Response({
            'errors': serializer.errors,
            'message': 'Login failed. Please check your credentials.'
        }, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Use AuthUtils for token revocation
            if AuthUtils.revoke_user_token(request.user):
                return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'No active token found'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'Logout failed'}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class TokenRefreshView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Use AuthUtils for token refresh
            token = AuthUtils.refresh_user_token(request.user)

            return Response({
                'token': token.key,
                'user': UserSerializer(request.user).data,
                'message': 'Token refreshed successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            # Print the exception for debugging purposes
            print(f"Token refresh error: {e}")
            return Response({
                'error': 'Token refresh failed'
            }, status=status.HTTP_400_BAD_REQUEST)
