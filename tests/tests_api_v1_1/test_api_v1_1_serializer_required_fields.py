# coding: utf-8
import json
from decimal import Decimal
from rest_framework.test import APITestCase
from rest_framework import status
from concrete_datastore.concrete.models import User, UserConfirmation, ItemPack
from django.test import override_settings


@override_settings(DEBUG=True)
class SerializerRequiredFieldsTestCase(APITestCase):
    """
    In this test class we will be creating 'ItemPack' instances
    with different data passed in the request in order to validate
    serializer required fields and validators.
    This model has the following fields with the following constraints:
        - field 'name' is required and cannot be NULL
        - field 'description' is not required
        - field 'status' is not required BUT if found, cannot be NULL
        - field 'nb_articles' is required and cannot be NULL
        - field 'cost' is not required BUT if found, cannot be NULL
        - field 'sold' is not required BUT if found, cannot be NULL
    The errors that may accur are the following:
        - ['This field is required.'] => 'required' validation
        - ['This field may not be blank.'] => 'empty_value' validation

    """

    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(
            email='johndoe@netsach.org', password='plop'
        )
        self.user.set_level('superuser')
        self.user.save()
        self.confirmation = UserConfirmation.objects.create(user=self.user)
        self.confirmation.confirmed = True
        self.confirmation.save()
        resp = self.client.post(
            '/api/v1.1/auth/login/',
            {"email": "johndoe@netsach.org", "password": "plop"},
        )
        self.token = resp.data['token']
        self.url = '/api/v1.1/item-pack/'

    def test_required_fields(self):
        #:  If name is not in request data
        resp = self.client.post(
            self.url, data={}, HTTP_AUTHORIZATION=f'Token {self.token}'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('description', resp.data)
        self.assertNotIn('status', resp.data)
        self.assertNotIn('cost', resp.data)
        self.assertNotIn('sold', resp.data)
        self.assertDictEqual(
            resp.data,
            {
                'name': ['This field is required.'],
                'nb_articles': ['This field is required.'],
            },
        )
        resp = self.client.post(
            self.url,
            data=json.dumps({}),
            HTTP_AUTHORIZATION=f'Token {self.token}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('description', resp.data)
        self.assertNotIn('status', resp.data)
        self.assertNotIn('cost', resp.data)
        self.assertNotIn('sold', resp.data)
        self.assertDictEqual(
            resp.data,
            {
                'name': ['This field is required.'],
                'nb_articles': ['This field is required.'],
            },
        )

    def test_valid_fields(self):
        #:  If no 'application/json' header is passed to request
        #:  the client will remove all keys where the the value
        #:  is an empty string (e.g. 'status')
        resp = self.client.post(
            self.url,
            data={
                'name': '',
                'description': '',
                'status': '',
                'cost': 0.0,
                'nb_articles': 0,
            },
            HTTP_AUTHORIZATION=f'Token {self.token}',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            resp.json(),
            {
                'name': ['This field may not be blank.'],
                'cost': ['This field may not be blank.'],
                'nb_articles': ['This field may not be blank.'],
            },
        )

        #:  The header 'application/json' allows to pass empty strings
        #:  in the request as well as the value 'None'
        resp = self.client.post(
            self.url,
            data=json.dumps(
                {
                    'name': '',
                    'description': '',
                    'status': '',
                    'cost': 0.0,
                    'sold': None,
                    'nb_articles': 0,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f'Token {self.token}',
        )
        self.assertNotIn('description', resp.json())
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            resp.json(),
            {
                'name': ['This field may not be blank.'],
                'status': ['This field may not be blank.'],
                'cost': ['This field may not be blank.'],
                'sold': ['This field may not be null.'],
                'nb_articles': ['This field may not be blank.'],
            },
        )

    def test_valid_data(self):
        self.assertEqual(ItemPack.objects.count(), 0)
        resp = self.client.post(
            self.url,
            data={'name': 'Test', 'nb_articles': 20},
            HTTP_AUTHORIZATION=f'Token {self.token}',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ItemPack.objects.count(), 1)
        item_pack = ItemPack.objects.first()
        self.assertEqual(item_pack.status, 'PENDING')  # default value
        self.assertEqual(item_pack.sold, False)  # default value
        self.assertEqual(item_pack.cost, Decimal(10))  # default value
