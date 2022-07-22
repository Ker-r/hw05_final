from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_author = Client()
        self.authorized_author.force_login(PostURLTests.user)
        self.user_not_author = User.objects.create_user(username='username')
        self.user_not_author_client = Client()
        self.user_not_author_client.force_login(self.user_not_author)

    def test_url_exists_at_desired_location(self):
        urls_name = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.user.username}/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/': HTTPStatus.OK,
        }
        for address, status in urls_name.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, status)

    def test_create_url_exists_at_desired_location(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_author.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            '/create/': 'posts/create.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_author.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_edit(self):
        reverse_user = reverse('users:login')
        reverse_name = reverse('posts:post_edit', args=(self.post.pk,))
        expected_url = f'{reverse_user}?next={reverse_name}'
        response_any = (
            self.client.get(reverse('posts:post_edit', args=(self.post.pk,)))
        )
        author_response = (
            self.authorized_author.get(reverse(
                'posts:post_edit', args=(self.post.pk,)))
        )
        self.assertTemplateUsed(author_response, 'posts/create.html')

        self.assertRedirects(
            response_any,
            expected_url
        )
        response_any = (
            self.user_not_author_client.get(reverse(
                'posts:post_edit', args=(self.post.pk,)))
        )
        self.assertRedirects(
            response_any, reverse('posts:post_detail', args=(self.post.pk,))
        )

    def test_page_404_template(self):
        response = self.authorized_author.get(
            reverse('posts:post_detail', args=(self.post.pk + 1, ))
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
