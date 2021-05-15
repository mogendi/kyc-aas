from django.contrib.auth.models import User
from rest_framework import serializers
from kycweb.models import ( NatId, KRAPinCert )

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'groups']

class NatIdSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = NatId
        fields = ['id_number', 'full_name', 'bdate', 'sex', 'district_ob', 'place_oi', 'issue_date']

class KRAPinSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = KRAPinCert
        fields = ['pin', 'taxpayer_name', 'addr', 'po_box', 'email']