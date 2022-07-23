from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Follow, Post

User = get_user_model()


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.author = User.objects.create_user(username='author')

    def setUp(self):
        self.guest_client = Client()
        self.auth_client = Client()
        self.auth_client.force_login(self.user)
        self.second_user = User.objects.create_user(username='second_user')
        self.second_user_client = Client()
        self.second_user_client.force_login(self.second_user)
        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_follow(self):
        """Тест подписки на автора"""
        follow_count = Follow.objects.count()
        self.auth_client.get(
            reverse(
                'posts:profile_follow',
                args=(self.author.username,)
            ),
            follow=True
        )
        self.assertTrue(
            self.user.follower.filter(author=self.author).exists()
        )
        response = self.auth_client.get(
            reverse('posts:profile', args=(self.author.username,)),
            follow=True
        )
        self.assertContains(
            response,
            'Отписаться'
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)

    def test_unfollow(self):
        follow_count = Follow.objects.count()
        Follow.objects.create(user=self.user, author=self.author)
        self.auth_client.get(
            reverse('posts:profile_unfollow', args=(self.author.username,)),
            follow=True
        )
        self.assertFalse(
            self.user.follower.filter(author=self.author).exists()
        )
        response = self.auth_client.get(
            reverse('posts:profile', args=(self.author.username,)),
            follow=True
        )
        self.assertContains(
            response,
            'Подписаться',
        )
        self.assertEqual(Follow.objects.count(), follow_count)

    def test_follow_index(self):
        follow_count = Follow.objects.count()
        data = {
            'text': 'Test text follow',
        }
        Follow.objects.create(user=self.user, author=self.author)
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        Post.objects.create(
            text=data['text'],
            author=self.author
        )
        response = self.auth_client.get(
            reverse('posts:follow_index'),
            follow=True
        )
        self.assertContains(
            response,
            data['text'],
        )
        response = self.second_user_client.get(
            reverse('posts:follow_index'),
            follow=True
        )
        self.assertNotContains(
            response,
            data['text'],
        )

    def test_follow_index_guest(self):
        follow_count = Follow.objects.count()
        Follow.objects.create(user=self.user, author=self.author)
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        data = {
            "unpost": "Unfollow posts"
        }
        Post.objects.create(
            author=self.author,
            text=data['unpost']
        )
        response = self.guest_client.get(
            reverse('posts:index'),
            follow=False
        )
        self.assertContains(
            response,
            data['unpost']
        )
