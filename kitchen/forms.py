from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Ingredient, Profile, Recipe, RecipeIngredient

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=80, label='Your name')
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['first_name', 'username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account already uses this email address.')
        return email

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'category', 'quantity', 'unit', 'expires_on']
        widgets = {'expires_on': forms.DateInput(attrs={'type': 'date'})}

    def clean_name(self):
        return ' '.join(self.cleaned_data['name'].strip().split()).lower()

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['reminder_days', 'email_reminders']


class AdminRecipeForm(forms.ModelForm):
    instructions = forms.CharField(
        label='Cooking steps',
        widget=forms.Textarea(attrs={'rows': 8, 'cols': 80, 'placeholder': 'Wash and chop the vegetables.\nHeat a little oil in a pan.\nCook until tender and serve.'}),
        help_text='Write one step per line. The app displays them as a numbered list.',
    )

    class Meta:
        model = Recipe
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['instructions'] = '\n'.join(self.instance.instructions)

    def clean_instructions(self):
        steps = [line.strip() for line in self.cleaned_data['instructions'].splitlines() if line.strip()]
        if not steps:
            raise forms.ValidationError('Add at least one cooking step.')
        return steps


class AdminRecipeIngredientForm(forms.ModelForm):
    class Meta:
        model = RecipeIngredient
        fields = '__all__'

    def clean_name(self):
        from .services import normalize
        return normalize(self.cleaned_data['name'])
