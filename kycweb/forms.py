from django import forms
from django.contrib.auth.models import User
from .models import Usr

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'email': forms.TextInput(attrs={'class': 'form-control',
                                            'aria-describedby': 'emailHelp',
            }), 
            'first_name': forms.TextInput(attrs={'class': 'form-control',
                                            'aria-describedby': 'emailHelp',
            }),
            'last_name': forms.TextInput(attrs={'class': 'form-control',
                                            'aria-describedby': 'emailHelp',
            }),
        }

class UsrForm(forms.ModelForm):
    class Meta:
        model = Usr
        fields = ['phone_number', 'profile_pic']