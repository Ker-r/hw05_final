from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()
GROUP_LIST = reverse('posts:group_list', args=('test-slug',))
PROFILE = reverse('posts:profile', args=('test_user',))


class PostViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug-2',
            description='Тестовое описание 2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.POST_EDIT = reverse('posts:post_edit', args=(cls.post.id,))

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.POST_DETAIL = reverse('posts:post_detail', args=(self.post.id,))

    def test_post_not_in_group(self):
        response_group = (
            self.authorized_client.get
            (reverse('posts:group_list', args=(self.group2.slug,)))
        )
        self.assertNotIn(self.post, response_group.context.get('page_obj'))

    def test_post_detail_show_correct_context(self):
        """Шаблон сформирован с правильным контекстом."""
        response = (
            self.authorized_client.get(self.POST_DETAIL).context.get('post')
        )
        self.assertEqual(response.text, self.post.text)
        self.assertEqual(response.author.username, self.user.username)
        self.assertEqual(response.group.title, self.group.title)
        self.assertEqual(response.group.description, self.group.description)

    def test_post_views_context(self):
        """URL-адрес использует соответствующий шаблон."""
        testing_pages_names = {
            reverse('posts:index'): 'page_obj',
            reverse('posts:group_list', args=(self.group.slug,)): 'page_obj',
            reverse('posts:profile', args=(self.user.username,)): 'page_obj',
            self.POST_DETAIL: 'post',
        }
        for value, method in testing_pages_names.items():
            with self.subTest(value=value):
                client = self.authorized_client.get(value)
                if method != 'post':
                    post = client.context.get(method)[0]
                else:
                    post = client.context.get(method)
                self.assertEqual(post.id, self.post.id)
                self.assertEqual(post.text, self.post.text)
                self.assertEqual(post.group, self.post.group)
                self.assertEqual(post.author, self.post.author)

    def test_cache_index(self):
        response = self.guest_client.get(reverse('posts:index'))
        posts = response.content
        Post.objects.create(
            text='Тестовый пост',
            author=self.user,
        )
        response_old = self.guest_client.get(reverse('posts:index'))
        old_posts = response_old.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        response_new = self.guest_client.get(reverse('posts:index'))
        new_posts = response_new.content
        self.assertNotEqual(old_posts, new_posts)


LIMIT_POST = 13


class PaginatorTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        for post in range(LIMIT_POST):
            cls.post = Post.objects.create(
                author=cls.user,
                group=cls.group,
                text='text'
            )

    def setUp(self):
        self.follower = User.objects.create_user(username='follower')
        self.follower_client = Client()
        self.follower_client.force_login(self.follower)
        self.follower_client.get(
            reverse(
                'posts:profile_follow',
                args=(self.user.username,)
            ),
            follow=True
        )

    def test_count_post(self):
        urls = (
            ('posts:index', None,),
            ('posts:group_list', (self.group.slug,),),
            ('posts:profile', (self.user.username,),),
            ('posts:follow_index', None,),
        )
        pages = (
            ('?page=1', settings.PAGE,),
            ('?page=2', LIMIT_POST - settings.PAGE,),
        )
        for name, args in urls:
            with self.subTest(name=name):
                for page, quantity in pages:
                    with self.subTest(page=page):
                        response = self.follower_client.get(
                            reverse(name, args=args) + page
                        )
                        self.assertEqual(
                            len(response.context.get('page_obj').object_list),
                            quantity
                        )
