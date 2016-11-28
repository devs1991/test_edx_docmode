from .models import ExtraInfo
from django.forms import ModelForm

class ExtraInfoForm(ModelForm):
    """
    The fields on this form are derived from the ExtraInfo model in models.py.
    """
    def __init__(self, *args, **kwargs):
        super(ExtraInfoForm, self).__init__(*args, **kwargs)
        self.fields['specialization'].error_messages = {
            "required": u"Please select your specialization.",
            "invalid": u"Invalid Specialization.",
        }

    def __init__(self, *args, **kwargs):
        super(ExtraInfoForm, self).__init__(*args, **kwargs)
        self.fields['regnum'].error_messages = {
            "required": u"Please insert your registeration number.",
            "invalid": u"Invalid registeration number.",
        }

    class Meta(object):
        model = ExtraInfo
        fields = ('specialization', 'regnum')