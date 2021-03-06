# -*- coding: utf-8 -*-
from __future__ import unicode_literals


import uuid
import requests

from django.contrib.auth.base_user import BaseUserManager
from django.utils import timezone


from django.db import models

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from django.contrib.auth.models import AbstractUser, UserManager


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)

class MyUserManager(BaseUserManager):
    def create_user(self, description, username, email, password, **extra_fields):

        if not username:
            raise ValueError('Users must have an username')

        if not email:
            raise ValueError('Users must have an email address')

        if not password:
            raise ValueError('Users must have a password')


        user = self.model(
            email       = self.normalize_email(email),
            username = username,
            description = description
        )

        # If this is the first user give him admin rights
        if Instance.objects.count() == 0:
            print("First user. Assigning admin priviledges.")
            user.is_admin = True
            user.is_superuser = True
            user.is_staff = True

        else:
            print("Ci sono "+str(Instance.objects.count())+" utenti")

        user.set_password(password)
        user.save(using=self._db)

        # If this is the first user create the group "GMQL-ALL"
        if Instance.objects.count() == 1:
            group = Group()
            group.owner = user
            group.name = "GMQL-ALL"
            group.save()


        # Create a group with the name of this user and add this user
        group = Group()
        group.owner = user
        group.name = user.username
        group.save()
        group.instances.add(user)
        group.save()

        # Add the user to group ALL
        all = Group.objects.get(name="GMQL-ALL")
        all.instances.add(user)
        all.save()

        return user

    def create_superuser(self, description, username, email,  password, **extra_fields):

        print("Creating superuser")

        user                = self.create_user( description, username, email, password)
        user.is_admin       = True
        user.is_superuser   = True
        user.is_staff       = True
        user.save(using=self._db)
        return user

class Instance(AbstractUser):
    email            = models.EmailField(max_length=254, unique=True)
    description      = models.CharField(max_length=50, null=True)
    creation_date    = models.DateTimeField(default=timezone.now, blank=True)

    REQUIRED_FIELDS = ['email']

    objects = MyUserManager()

    def __str__(self):
        return self.username


class Location(models.Model):
    name = models.CharField(max_length=50)
    details = models.CharField(max_length=300)
    URI = models.CharField(max_length=100)
    alive = models.BooleanField(default=True)

    instance = models.OneToOneField(
        Instance,
        on_delete=models.CASCADE,
        to_field='username',
        primary_key=True
    )

    def checkAlive(self):
        print("checking")
        response = None
        try:
            response = requests.get(self.URI+"api-info", timeout=7)
            print(response)
            if (response != None and response.status_code == 200 and "gmql-federated-api" in response.content):
                self.alive=True
            else:
                self.alive=False

        except:
            self.alive=False
        finally:
            self.save()
            
    def __str__(self):
        return self.name + " ( " + self.URI + " )"

class Group(models.Model):
    name       = models.CharField(max_length=50, primary_key=True)
    owner      = models.ForeignKey(Instance, to_field='username', on_delete=models.CASCADE, editable=False)

    instances  = models.ManyToManyField(Instance, related_name='group_instance')

    def delete(self,  using=None, keep_parents=False):
        print("deleting "+ self._get_pk_val())

        for ds in Dataset.objects.filter(allowed_to__in=[ self._get_pk_val()]):
            # ds is a dataset containing that group
            new_allowed = Dataset.objects.get(pk=ds.pk).allowed_to.exclude(pk=self._get_pk_val())
            old_copies  = Dataset.objects.get(pk=ds.pk).copies.all()

            if not "GMQL-ALL" in map(lambda group: group.name, new_allowed):
                allowed_instances = []
                for gp in new_allowed:
                    allowed_instances += Group.objects.get(name=gp.name).instances.all()

                to_delete = set(old_copies).difference(set(allowed_instances))
                new_copies = set(old_copies).difference(to_delete)
                ds.copies = new_copies
                ds.save()

        return super(Group, self).delete(using=None, keep_parents=False)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):

        print("updating "+ self._get_pk_val())

        to_return =  super(Group, self).save(force_insert=False, force_update=False, using=None,
             update_fields=None)

        for ds in Dataset.objects.filter(allowed_to__in=[ self._get_pk_val()]):
            # ds is a dataset containing that group
            new_allowed = Dataset.objects.get(pk=ds.pk).allowed_to.all()
            old_copies  = Dataset.objects.get(pk=ds.pk).copies.all()

            if not "GMQL-ALL" in map(lambda group: group.name, new_allowed):
                allowed_instances = []
                for gp in new_allowed:
                    allowed_instances += Group.objects.get(name=gp.name).instances.all()

                to_delete = set(old_copies).difference(set(allowed_instances))
                new_copies = set(old_copies).difference(to_delete)
                ds.copies = new_copies
                ds.save()

        return to_return



    def __str__(self):
        return self.name + " (created by " + self.owner.username + ")"



class Dataset(models.Model):
    name = models.CharField(max_length=50)
    author = models.CharField(max_length=50, default="")
    description = models.CharField(max_length=300, default="")
    pub_date = models.DateTimeField(default=timezone.now)

    owner = models.ForeignKey(Instance, to_field='username', on_delete=models.CASCADE, editable=False)

    allowed_to = models.ManyToManyField(Group, related_name='dataset_group')

    copies =  models.ManyToManyField(Instance, related_name='dataset_instance')


    @property
    def dataset_identifier(self):
        return self.owner_id + "." + self.name

    class Meta:
        unique_together = (("name", "owner"),)

    def __str__(self):
        return self.dataset_identifier

class Authentication(models.Model):

    EXPIRATION_DAYS = 14

    client = models.ForeignKey(Instance, to_field='username', related_name='client', on_delete=models.CASCADE, editable=False)
    target = models.ForeignKey(Instance, to_field='username', related_name='target', on_delete=models.CASCADE)
    token = models.CharField(max_length=50, editable=False)
    expiration = models.DateTimeField(blank=True, editable=False, default=timezone.now)

    # Generate a token and expiration date on saving
    def save(self, *args, **kwargs):
            self.token = uuid.uuid4()
            self.expiration = timezone.now() + timezone.timedelta(days=self.EXPIRATION_DAYS)
            super(Authentication, self).save()

    @property
    def authentication_identifier(self):
        return str(self.client.username) + "_" + self.target.username

    class Meta:
        unique_together = (("client", "target"),)

    def __str__(self):
        return self.authentication_identifier




