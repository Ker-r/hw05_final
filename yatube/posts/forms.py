from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'text': 'Текст статьи',
            'group': 'Группа, к которой относится статья',
        }
        help_texts = {
            'text': 'Это поле не должно быть пустым',
            'group': 'Это поле необязательное',
        }

    def clean_text(self):
        if len(self.cleaned_data['text'].strip()) == 0:
            raise forms.ValidationError(
                'Поле с текстом статьи не должно быть пустым'
            )
        return self.cleaned_data['text']


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text', )
