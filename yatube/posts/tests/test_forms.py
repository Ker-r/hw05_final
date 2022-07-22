import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем запись в базе данных для проверки сушествующего slug
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            group=cls.group,
            image=cls.uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)

    def test_create(self):
        # Подсчитаем количество записей в Task
        post_count = Post.objects.count()
        form_data = {
            'group': self.group.id,
            'text': 'Тестовый текст',
            'image': self.uploaded,
        }
        # Отправляем POST-запрос
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        post = Post.objects.last()
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(post.image)

    def test_img_in_contest_pages(self):
        urls = (
            ('posts:index', None),
            ('posts:profile', (self.user.username, )),
            ('posts:group_list', (self.group.slug, )),
            ('posts:post_detail', (self.post.pk, )),
        )
        for name, args in urls:
            with self.subTest(name=name):
                response = self.authorized_client.get(reverse(name, args=args))
                post_img_in_context = Post.objects.first()
                self.assertTrue(post_img_in_context.image)
                self.assertContains(response, '<img')

    def test_create_post_form(self):
        post_count = Post.objects.count()
        form_data = {
            'text': 'Новый пост',
            'group': self.group.pk,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )

        self.assertEqual(Post.objects.count(), post_count + 1)
        last_post = Post.objects.all().first()
        self.assertEqual(last_post.text, form_data['text'])
        self.assertEqual(last_post.group_id, form_data['group'])
        self.assertEqual(last_post.author, self.user)
        self.assertTrue(last_post.group)
        self.assertRedirects(response, reverse(
            'posts:profile', args=(self.user.username, )))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit(self):
        change_group = Group.objects.create(
            title='test-group',
            slug='test-slug-2',
            description='Тестовое описание 2',
        )
        form_data = {
            'text': 'Данные из формы',
            'group': change_group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(self.post.pk,)),
            data=form_data,
            follow=True,
        )
        post = Post.objects.get(pk=self.post.pk)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(
            post.text,
            form_data['text']
        )
        self.assertEqual(post.group.id, change_group.id)
        response_change_group = self.authorized_client.post(
            reverse('posts:group_list', args=(self.group.slug,)),
        )
        self.assertEqual(response_change_group.status_code, HTTPStatus.OK)
        self.assertFalse(
            response_change_group.context['page_obj'].object_list
        )

    def test_post_create_guest(self):
        posts_count = Post.objects.count()
        reverse_user = reverse('users:login')
        reverse_name = reverse('posts:post_create')
        redirect_url = f'{reverse_user}?next={reverse_name}'
        form_date = {
            'text': 'test text',
            'group': self.group.id,
        }
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_date,
            follow=True
        )
        self.assertRedirects(response, redirect_url)
        self.assertEqual(posts_count, Post.objects.count())

    def test_comment_auth_form(self):
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Новый пост',
        }
        self.authorized_client.post(
            reverse('posts:add_comment', args=(self.post.pk, )),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)

    def test_comment_guest_form(self):
        reverse_user = reverse('users:login')
        reverse_name = reverse('posts:add_comment', args=(self.post.id, ))
        redirect_url = f'{reverse_user}?next={reverse_name}'
        comment_count = Comment.objects.count()
        form_date = {
            'text': 'test text',
        }
        response = self.client.post(
            reverse('posts:add_comment', args=(self.post.id, )),
            data=form_date,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_count)
        self.assertRedirects(response, redirect_url)
