from django.contrib.auth.models import User
from rest_framework import viewsets
from rest_framework import permissions
from .serializers import UserSerializer
from kycweb.models import ( ChestRegistry, Chest, Corporation, Usr, 
                            HitsRegistry,HostRegistry, CorpKeyUses, NatId, KRAPinCert, 
                            Validator, ValInstance, Authenticator )
from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings
from .serializers import NatIdSerializer, KRAPinSerializer

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

'''
Check if a user is authenticated for a certain application
'''
@csrf_exempt
def query_auth(r):
    if r.method == "POST":
        if r.headers['content-type'] == 'application/json':
            # mut = r.POST._mutable
            # r.POST._mutable = True
            r.POST = json.loads(r.body.decode('utf-8'))
            # r.POST._mutable = mut

        host = r.META['REMOTE_ADDR']
        print(host)
        hst = key = corp = app = doctype = num = nid = None

        # the corporation key required for identifying the corporation
        try:
            key = r.POST.get('key')
        except:
            return JsonResponse({"error": "key required"})
        try:
            corp = Corporation.objects.get(key=key)
        except:
            return JsonResponse({"error": "Invalid key"})
        if not corp.enabled:
            return JsonResponse({"error": "The key is disabled"})

        # TODO: host required for checking if its verified [needs a reverse DNS request for non ip hosts]
        try:
            hst = HostRegistry.objects.get(host=host)
        except:
            return JsonResponse({"error": "This host is unregistered"})

        # create a use for the corporations key
        ku = CorpKeyUses.objects.create(host=hst, complete=False)

        # the query document
        try:
            doctype = r.POST.get('doc_type')
        except:
            return JsonResponse({"error": "document type required"})
        try:
            num = r.POST.get('doc_number')
        except:
            return JsonResponse({"error": "document number required"})

        # the application being searched
        try:
            app = r.POST.get('application')
        except:
            return JsonResponse({"error": "application required"})

        # try grab the document
        if doctype == "national_id":
            try:
                nid = NatId.objects.get(id_number=num)
            except:
                return JsonResponse({"error": "This user is unauthenticated"})
        elif doctype == "kra_pin":
            try:
                nid = KRAPinCert.objects.get(pin=num)
            except:
                return JsonResponse({"error": "This user is unauthenticated"})
        else:
            return JsonResponse({"error": "Allowed document types: national_id or kra_pin"})

        
        # check the corporations permissions
        usr = nid.usr
        chest = perm = None
        try:
            chest = Chest.objects.get(created_by=usr, application=app)
        except:
            return JsonResponse({"error": "This user is unauthenticated or the application is invalid"})
        try:
            perm = ChestRegistry.objects.get(corporation=corp, chest=chest)
        except:
            return JsonResponse({"error": "This user has not enable permissions for the corporation"})
        if not perm.access:
            return JsonResponse({"error": "This user has not enable permissions for the corporation"})

        HitsRegistry.objects.create(corporation=corp, chest=chest)

        # response
        resp = {
            "authenticated": True,
            "user key": usr.ctx_id 
        }

        ku.complete = True
        ku.save()

        return JsonResponse(resp)

    else:
        return JsonResponse({"error": "The request method is POST"})

'''
grabs a specified document
'''
@csrf_exempt
def get_document(r):
    if r.method == "POST":
        if r.headers['content-type'] == 'application/json':
            # mut = r.POST._mutable
            # r.POST._mutable = True
            r.POST = json.loads(r.body.decode('utf-8'))
            # r.POST._mutable = mut

        doc = key = ukey = num = hst = serialzed = None

        # check the corp key
        try:
            key = r.POST.get('key')
        except:
            return JsonResponse({'error': 'key field required'})
        try:
            key = Corporation.objects.get(key=key)
        except:
            return JsonResponse({'error': 'invalid key'})

        # TODO: host required for checking if its verified [needs a reverse DNS request for non ip hosts]
        host = r.META['REMOTE_ADDR']
        try:
            hst = HostRegistry.objects.get(host=host)
        except:
            return JsonResponse({"error": "This host is unregistered"})

        # create a key use
        ku = CorpKeyUses.objects.create(host=hst, complete=False)

        # check user key
        try:
            ukey = r.POST.get('user')
        except:
            return JsonResponse({"error": "user key required"})
        usr = None
        try:
            usr = Usr.objects.get(ctx_id=ukey)
        except:
            return JsonResponse({"error": "the user key is invalid"})

        # check document/type
        nid = None
        try:
            doc = r.POST.get('doc_type')
        except:
            return JsonResponse({"error": "doc_type required"})
        if doc == 'national_id':
            try:
                nid = NatId.objects.get(usr=usr)
                serialzed = NatIdSerializer(nid)
            except:
                return JsonResponse({"error": "This user doesn't have the requested document"})
        elif doc == "kra_pin":
            try:
                nid = KRAPinCert.objects.get(usr=usr)
                serialzed = KRAPinSerializer(nid)
            except:
                return JsonResponse({"error": "This user doesn't have the requested document"})
        else:
            return JsonResponse({"error": "Allowed document types: national_id or kra_pin"})

        # check permissions
        perm = None
        try:
            perm = ChestRegistry.objects.get(chest=nid.file.chest, corporation=key)
        except:
            return JsonResponse({"error": "This user has not enabled permissions for the corporation"})
        if not perm.access:
            return JsonResponse({"error": "This user has not enabled permissions for the corporation"})

        ku.complete = True
        ku.save()

        HitsRegistry.objects.create(corporation=key, chest=nid.file.chest)

        return JsonResponse(serialzed.data)

    else:
        return JsonResponse({"error": "The request method is POST"})

# get auth for validator
@csrf_exempt
def get_auth(r):
    if r.method == "POST":
        if r.headers['content-type'] == 'application/json':
            # mut = r.POST._mutable
            # r.POST._mutable = True
            r.POST = json.loads(r.body.decode('utf-8'))
            # r.POST._mutable = mut

        doc = key = ukey = num = hst = serialzed = None

        # check the corp key
        try:
            key = r.POST.get('key')
        except:
            return JsonResponse({'error': 'key field required'})
        try:
            key = Corporation.objects.get(key=key)
        except:
            return JsonResponse({'error': 'invalid key'})

        # TODO: host required for checking if its verified [needs a reverse DNS request for non ip hosts]
        host = r.META['REMOTE_ADDR']
        try:
            hst = HostRegistry.objects.get(host=host)
        except:
            return JsonResponse({"error": "This host is unregistered"})

        # create a key use
        ku = CorpKeyUses.objects.create(host=hst, complete=False)

        # check user key
        try:
            ukey = r.POST.get('user')
        except:
            return JsonResponse({"error": "user key required"})
        usr = None
        try:
            usr = Usr.objects.get(ctx_id=ukey)
        except:
            return JsonResponse({"error": "the user key is invalid"})

        # check validator
        vl = None
        try:
            vl = Authenticator.objects.get(name=r.POST.get("auth_name"))
        except:
            return JsonResponse({"error": "that authenticator doesn't exist"})

        vl = Validator.objects.filter(auth_model=vl, internal=False)
        print(vl)

        try:
            vl = ValInstance.objects.get(usr=usr, val=vl[0])
            print(vl.pk)
        except:
            return JsonResponse({"error": "User isn't validated for that application"})

        ku.complete = True
        ku.save()

        return JsonResponse({'doc': vl.ident})