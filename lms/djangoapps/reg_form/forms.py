from .models import extrafields
from django import forms
from django.conf import settings
from lms.djangoapps.specialization.models import specializations
from lms.djangoapps.hcspecialization.models import hcspecializations

class regextrafields(forms.ModelForm):

    reg_num = forms.CharField(
        label='Medical Registration Number',
        min_length=5,
        error_messages={
            "min_length": "Atleast five charac",
        }
    )

    address = forms.CharField(
        label='Address',
        min_length=15,
        required=False,
        error_messages={
            "min_length": "Adress needs to be Atleast fifteen characters",
        }
    )

    specialization = forms.ModelChoiceField(
        queryset=specializations.objects.all(),
        empty_label="select your specialization",
        label='Specialization',
        required=False
    )
    
    hcspecialization = forms.ModelChoiceField(
        queryset=hcspecializations.objects.all(),
        empty_label="select your specialization",
        label='Health care specialization',
        required=False

    )
        
    USER_TYPE = (
        ('dr', 'Doctor'),
        ('u', 'User'),
        # Translators: 'Other' refers to the student's gender
        ('ms', 'Medical Student'),
        ('hc', 'Health Care Proffessional')
    )

    user_type = forms.ChoiceField(
        label='User Type',
        widget=forms.Select(attrs={"onChange":'usertype()'}),
        choices=USER_TYPE,
        required=True
    )


    def clean(self, *args, **kwargs):
        reg_num = self.cleaned_data["reg_num"]
        address = self.cleaned_data["address"]

    class Meta(object):
        model = extrafields
        fields = ('user_type','reg_num','address','specialization','hcspecialization')

    

