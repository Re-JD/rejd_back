from django.shortcuts import render
from .serializers import RegisterSerializer, EmailVerificationSerializer
from rest_framework import generics, status, views
from rest_framework.response import Response
from .models import User
from rest_framework_simplejwt.tokens import RefreshToken
from .utils import Util
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
import jwt
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# Create your views here.
class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    
    def post(self, request):
        user = request.data
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user_data = serializer.data
        
        user = User.objects.get(email=user_data['email'])
        token = RefreshToken.for_user(user).access_token
        current_site = get_current_site(request).domain
        relativeLink = reverse('email-verify')
        absurl = 'http://' + current_site + relativeLink + '?token=' + str(token)
        email_body = 'Hi ' + user.username + ', use link below to verify your email \n' + absurl
        data = {
            'email_body' : email_body,
            'email_subject': 'Verify your email',
            'to_email' : user.email,
        }
        Util.send_email(data) 
        return Response(user_data, status=status.HTTP_201_CREATED)

class VerifyEmail(views.APIView):
    serializer_class = EmailVerificationSerializer
    token_param_config = openapi.Parameter(
        'token',
        in_=openapi.IN_QUERY,
        description='Description',
        type=openapi.TYPE_STRING,
        )

    @swagger_auto_schema(manual_parameters=[token_param_config])
    def get(self, request):
        token = request.GET.get('token')
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS512'])
            user = User.objects.get(id=payload['user_id'])
            if not user.is_verified:
                user.is_verified = True
            user.save()
            return Response({'email': 'Successfully activated'}, status=status.HTTP_200_OK)
        
        except jwt.ExpiredSignatureError as error:
            return Response({'error':'Activation expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        except jwt.exceptions.DecodeError as error:
            return Response({'error':'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)