from django import forms
from .models import Doctor, Appointment

class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['name', 'email', 'phone', 'specialization', 'experience', 'qualification', 'address', 'photo']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            if photo.size > 2 * 1024 * 1024:
                raise forms.ValidationError('Photo size must be less than 2MB')
            if not photo.content_type in ['image/jpeg', 'image/png']:
                raise forms.ValidationError('Only JPG and PNG images are allowed')
        return photo

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['patient_name', 'patient_email', 'patient_phone']
