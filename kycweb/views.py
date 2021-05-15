from json.encoder import JSONEncoder
from django import views
from django.http import request
from django.http.response import Http404
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from face_recognition.api import face_encodings, face_locations
from .forms import UserForm, UsrForm, FileForm
from .models import ( BankingChestType, ChestRegistry, Chest, Corporation, 
                      Usr, FileInstances, HitsRegistry, WorkChestType, 
                      Validator, HostRegistry, CorpKeyUses )
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import FileSystemStorage
import pathlib, os, sys, pytesseract, pdf2image, PIL, io, numpy, re, requests, json, Levenshtein as lev, datetime, face_recognition, cv2
from PIL import ImageEnhance, ImageOps
from django.conf import settings
from django.db.models import Q
from .tasks import file_type, file_contents, new_file, image_extractor, unpack_id, unpack_kra

LIMIT = 100000000

'''
Uploading files from user to 
destination folder
'''
def upload_file(f, d):
    with open(d, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

'''
Creating both the default and extended
user
'''
def create_user(r):
    registered = False
    if r.method == "POST":
        user_form = UserForm(data=r.POST)
        usr_f = UsrForm(data=r.POST)

        if user_form.is_valid() and usr_f.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()
            usr = usr_f.save(commit=False)
            usr.def_usr = user

            if 'profile_pic' in r.FILES:
                usr.profile_pic = r.FILES['profile_pic']

            usr.save()
            registered = True
            return redirect('/login')
        else:
            print(user_form.errors, usr_f.errors)
    else:
        user = UserForm()
        usr = UsrForm

    return render(r, 'registration/signup', {'reg': registered})

'''
The contact location/ dashboard where users
view information like available space the
chests they've created and links that they can create
'''
@login_required
def home(r):
    return render(r, 'kycweb/dash.html')

class GeneralChests():

    def remove_dups(l):
        non_dup = []
        dup = False
        for i in l:
            for j in non_dup:
                if i.usr.id == j.usr.id and i.chest.id == j.chest.id:
                    dup = True
            if not dup:
                non_dup.append(i)
            else:
                dup = False
        return non_dup[:5]

    '''
    Loads chest data & information and renders chests UI
    '''
    @login_required
    def chests(r):
        n_chests = n_hits = n_size = 0
        dng = False
        usr = Usr.objects.get(def_usr=r.user.id)
        chests = Chest.objects.filter(created_by=usr.id)
        hits = HitsRegistry.objects.filter(chest__created_by__def_usr__id=r.user.id).order_by('-tstmp')
        n_hits = hits.count()
        n_chests = chests.count()
        recent_opens = HitsRegistry.objects.filter(usr=usr)
        if n_chests>0:
            for i in chests:
                n_size += int(i.chest_size)/1000000
        else:
            n_size = n_size
        if (n_size/LIMIT)*100 <= 5 and (n_size/LIMIT)*100 > 0 and n_size>1:
            dng = True
        return render(r, 'kycweb/chests.html', {'chests':chests, 
                                            'n_chests':n_chests, 
                                            'size':n_size, 
                                            'lim':LIMIT/1000000,
                                            'dng': dng,
                                            'n_hits': n_hits,
                                            'recents': GeneralChests.remove_dups(recent_opens),
                                            'hits': hits[:2]
                                            })

    def open_chest(r):
        chest = Chest.objects.get(chest_ID=r.POST.get("chest"))
        auth = usr = None
        try:
            usr = Usr.objects.get(def_usr=r.user.id)
            try:
                auth = ChestRegistry.objects.get(chest=chest, usr=usr)
            except:
                return HttpResponse("You're not authenticated for this chest")
        except:
            return HttpResponse("You're not authenticated for this chest")

        if not auth.access:
            return HttpResponse("You're not authenticated for this chest")

        if chest is None:
            return HttpResponse("The chest key is invalid")
        files = FileInstances.objects.filter(chest=chest)
        HitsRegistry.objects.create(usr=usr, chest=chest)

        ctx = {
            "files": files,
            "user": False,
            "chest": chest
        }
        return render(r, "kycweb/files.html", ctx)

    def search_chest(r):
        chest = None
        try:
            chest = Chest.objects.get(chest_ID=r.POST.get("chest"))
        except:
            return JsonResponse({"error": "Error searching, please reload page"})

        query = r.POST.get("query")

        files = FileInstances.objects.filter(chest=chest, upload_path__contains=query)

        ctx = {
            'files': files,
            'user': False,
            'chest': chest
        }

        return render(r, "kycweb/files.html", ctx)

    def view_hits(r):
        hits = HitsRegistry.objects.filter(chest__created_by__def_usr__id=r.user.id).order_by('-tstmp')

        return render(r, 'kycweb/hits.html', {'hits': hits})

'''
Get a bearer token for the searches
'''
def get_bearer_token():
    data = {
        "username": "8448779624",
        "password": "qbHfd0CuiElByORb2VSkw55fTnXRHPlN"
    }
    headers = {
        "Authorization": "Basic TENkRjdjd2RWclN3YmtOOVppNUdyd2ZNRTNDSVFveUU6VnM3a3dwemVaVjRwSklBbA=="
    }
    r = requests.post("https://sandbox.jengahq.io/identity-test/v2/token/", data=data, headers=headers)
    print(r)
    return r

'''
Accepts ID uploads and checks their validity, ext of new file
'''
def check_id(r):
    fa = r.FILES.get("userid")
    idn = image_extractor(r'[0-9]{8}', fa)
    uname = image_extractor(r"(FULL NAMES)[ |\n]*([A-Z'’ ]+ [A-Z'’ ]+ [A-Z'’ ]*)", fa)
    if uname is False:
        ctx = {
            'verified': False,
        }
        return JsonResponse(ctx)
    uname = re.search(r"[A-Z'’ ]+ [A-Z'’ ]+ [A-Z'’ ]*", uname).group()
    bday = image_extractor(r'(DATE OF BIRTH)[ |\n]*[0-9]{2}[. ,]+[0-9]{2}[. ,]+[0-9]{4}', fa)
    bday = re.search(r'[0-9]{2}[. ,]+[0-9]{2}[. ,]+[0-9]{4}', bday).group()
    print(r.POST.get("bd"))
    if idn:
        headers = {
            "Authentication": str(get_bearer_token())
        }
        data = {
            "id": "34938447"
        }
        ro = requests.post("https://sandbox.jengahq.io/identity-test/v2/token", headers=headers, data=data).json()
        if lev.distance(uname, r.POST.get("uname").upper()) < 7:
            dtb = datetime.datetime.strptime(r.POST.get("bd"), '%Y-%m-%d').strftime('%d.%m.%y')
            print(dtb) 
            if lev.distance(bday, dtb) < 7:
                ctx = {
                    'verified': True,
                }
            else:
                ctx = {
                    'verified': False,
                }
        else:
            ctx = {
                'verified': False
            }
        return JsonResponse(ctx)
    else:
        print(idn)
        ctx = {
            'verified': False,
        }
        return JsonResponse(ctx)

'''
Accept KRA files and checks their validity
'''
def check_kra(r):
    fa = r.FILES.get("userkra")
    idn = image_extractor(r'[A-G][0-9]{9}[A-G]', fa)
    uname = image_extractor(r"(Taxpayer Name)[ \n]*([A-Z'’ ]+ [A-Z'’ ]+ [A-Z'’ ]*)", fa)
    if uname is False:
        ctx = {
            'verified': False,
        }
        return JsonResponse(ctx)
    uname = re.search(r"[A-Z'’ ]+ [A-Z'’ ]+ [A-Z'’ ]*", uname).group()
    addr_check = []
    addr_check.append(image_extractor(i, fa) for i in r.POST.get("uaddress").split())
    for i in addr_check:
        count = 0
        if i is False:
            count+=1
        if count > 3:
            ctx = {
                'verified': False
            }
            return JsonResponse(ctx)
    print(uname)
    if idn:
        print(idn)
        if lev.distance(uname, r.POST.get("uname").upper()) < 7:
            ctx = {
                'verified': True,
            }
        else:
            ctx = {
                'verified': False
            }
        return JsonResponse(ctx)
    else:
        ctx = {
            'verified': False
        }
        return JsonResponse(ctx)

'''
Checks passport photos relative to the id_pic
decides validity based on distance
'''
def check_pic(r):
    ids = file_contents(r.FILES.get("userid"))
    pps = file_contents(r.FILES.get("pic"))
    loc_pp = face_locations(pps[0])
    print(ids[0])
    for id in ids:
        loc = face_locations(id)
        enc = face_encodings(id, loc)
        pp = face_encodings(pps[0], loc_pp)
        print(loc)
        ds = face_recognition.face_distance(enc, pp)
        print(ds)
    ctx = {"verified": True}
    return JsonResponse(ctx)
    
'''
All file manipulation semantics
'''
class FileOperations():

    def delete_file(r, fid):
        f = FileInstances.objects.get(pk=fid)
        os.remove(f.upload_path)
        c = f.chest
        if c.auth_chest:
            ac = None
            try:
                ac = BankingChestType.objects.get(abstract_chest=c)
            except:
                try:
                    ac = WorkChestType.objects.get(abstract_chest=c)
                except:
                    ac = None
            if ac is not None:
                f.delete()
                lv = ac.gen_auth_level()
                ctx = {"deleted": True, "level":lv}
                return JsonResponse(ctx)
            else:
                return Http404
    
    def create_file(r):
        pass

    def download_file(r, fid):
        f = FileInstances.objects.get(pk=fid)
        file_path = os.path.join(settings.BASE_DIR, f.upload_path)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fa:
                if f.file_type is 'document':
                    rsp = HttpResponse(fa.read(), content_type="application/pdf")
                else:
                    ft = pathlib.Path(fa.name).suffix[1:]
                    rsp = HttpResponse(fa.read(), content_type="image/" + ft)
                rsp['Content-Disposition'] = 'inline; filename=' + f.get_file_name()
                return rsp
        return Http404

'''
New chest post form loader
'''
class ChestCreateView(LoginRequiredMixin, generic.View):
    model = FileInstances
    fileformclass = FileForm
    login_url = 'login/'   

    def get(self, r):
        fileform = self.fileformclass(None)
        return render(r, 'kycweb/new_chest.html', {'form': fileform})

    def post(self, r):
        chest_type = r.POST.get('chest-types')
        print(chest_type)
        if chest_type == "oth":
            usr = Usr.objects.get(def_usr=r.user.id)
            chest = Chest.objects.create(chest_name=r.POST.get('chest-name'), chest_size=0, created_by=usr)
            nfls = int(r.POST.get('size-flag'))
            for i in range(0, nfls):
                new_file(chest, r)
        if chest_type is "bnk":
            return requests.post("new_chest/bnk/", data=r)
        if chest_type is "wrk":
            return requests.post("new_chest/wrk/", data=r)
        return redirect("/")

'''
Chest view loader
'''
class ChestView(LoginRequiredMixin, generic.View):
    login_url = 'login/'

    def get(self, r, slug):
        chest = Chest.objects.get(chest_ID=slug)
        files = FileInstances.objects.filter(chest=chest)
        usrs = ChestRegistry.objects.filter(chest=chest)
        authc = None
        if chest.auth_chest:
            try:
                authc = BankingChestType.objects.get(abstract_chest=chest)
            except:
                try:
                    authc = WorkChestType.objects.get(abstract_chest=chest)
                except:
                    chest.auth_chest = False
        ctx = {
            "chest": chest,
            "files": files,
            "users": usrs,
            "ac": authc
        }
        return render(r, "kycweb/chest.html", ctx)

    def extend_auth(r,c):
        pass

    def extend_chest(r):
        chest = Chest.objects.get(pk=r.POST.get("chest"))
        ctx = {
            "files": new_file(chest, r),
            "user": True
        }
        return render(r, "kycweb/files.html" ,ctx)

    def get_indiv_perm(r, pid):
        perm = ChestRegistry.objects.get(pk=pid)
        if perm.corporation is not None:
            print(perm.corporation.name)
        ctx = {
            "u": perm,
        }
        return render(r, "kycweb/perm.html", ctx)

    def change_permissions(r, reg_id):
        reg = ChestRegistry.objects.get(pk=reg_id)
        if reg.access:
            reg.access = False
        else:
            reg.access = True
        reg.save()
        ctx = {"state": reg.access}
        return JsonResponse(ctx)

    def remove_permissions(r, reg_id):
        reg = ChestRegistry.objects.get(pk=reg_id)
        reg.delete()
        ctx = {"deleted": True}
        return JsonResponse(ctx)

    def add_permissions(r, uid):
        u = c = None
        try:
            u = Usr.objects.get(ctx_id=uid)
        except:
            print("Not a user")
        try:
            c = Corporation.objects.get(key=uid)
        except:
            print("Not a corporation")
        try:
            ch = Chest.objects.get(chest_ID=r.POST.get('chest'))
            if ch is not None:
                if u is not None and c is None:
                    try:
                        ChestRegistry.objects.get(usr=u, chest=ch)
                        return JsonResponse({"error": "This user already has permissions"})
                    except:
                        cr = ChestRegistry.objects.create(usr=u, chest=ch, access=True)
                        ctx = {"registry":cr.id}
                        return JsonResponse(ctx)
                elif u is None and c is not None:
                    try:
                        ChestRegistry.objects.get(corporation=c, chest=ch)
                        return JsonResponse({"error": "This corporation already has permissions"})
                    except:
                        cr = ChestRegistry.objects.create(corporation=c, chest=ch, access=True)
                        ctx = {"registry":cr.id}
                        return JsonResponse(ctx)
                elif u is not None and c is not None:
                    ctx = {"error": "There was an issue creating this permission"}
                    return JsonResponse(ctx)
                else:
                    ctx = {"error": "This user/corporation does not exist"}
                    return JsonResponse(ctx)
        except:
            ctx = {"error": "The was an issues processing this request"}

'''
New Banking auth instance. This 
only exists as a generic implementation
and extention of the ChestCreateView 
'''
class BankingChestCreateView(LoginRequiredMixin, generic.View):
    models = BankingChestType
    login_url = 'login/'

    def post(self, r):
        # by the time the view is at this point 
        # all docs have been verified to an extent
        usr = Usr.objects.get(def_usr=r.user.id)
        chest_type = r.POST.get('chest-types')
        if chest_type == "bnk":
            print(chest_type)
            chest = Chest.objects.create(
                chest_name="banking".format(r.POST.get("uname")), chest_size=0, created_by=usr, auth_chest=True, application='banking')
            chest.save()
            bnk_id = new_file(chest, r, "userid")
            bnk_kra = new_file(chest, r, "userkra")
            bnk_util = new_file(chest, r, "userutil")
            usr_pp = new_file(chest, r, "userpp")
            usr.addr      = r.POST.get("uaddress"), 
            usr.bdate     = r.POST.get("bd"), 
            usr.full_name =r.POST.get("uname").upper()
            usr.profile_pic = usr_pp.upload_path
            usr.save()
            
            unpack_id(r, bnk_id)
            unpack_kra(r, bnk_kra)

            b = BankingChestType.objects.create(
                abstract_chest=chest, bnk_id=bnk_id, kra=bnk_kra, utility=usr_pp)
            b.gen_auth_level()
            return redirect("/")

'''
New Work auth instance. This 
only exists as a generic implementation
and extention of the ChestCreateView as well. 
'''
class WorkChestCreateView(LoginRequiredMixin, generic.View):
    models = WorkChestType
    login_url = 'login/'

    def post(self, r):
        usr = Usr.objects.get(def_usr=r.user.id)
        chest_type = r.POST.get('chest-types')
        if chest_type is "wrk":
            chest = Chest.objects.create(
                chest_name="wrk-".format(r.POST.get("uname")), chest_size=0, created_by=usr)
            chest.save()
            wrk_id = new_file(chest, r, "userid")
            wrk_kra = new_file(chest, r, "userkra")
            wrk_nhif = new_file(chest, r, "usernhif")
            wrk_nssf = new_file(chest, r, "usernssf")
            cogc = new_file(chest, r, "cogc")
            WorkChestType.objects.create(
                abstract_chest=chest, wrk_id=wrk_id, kra=wrk_kra, nhif=wrk_nhif, nssf=wrk_nssf, cogc=cogc)
            return redirect("/")

'''
Delete chest view, has to somehow track
if the chest has any generic extentions
'''
class DeleteChest(LoginRequiredMixin, generic.View):
    login_url = 'login/'

    def get(self, r, slug):
        chest = Chest.objects.get(chest_ID=slug)
        chest.delete()
        return redirect('/')

    def post(self, r, slug):
        chest = Chest.objects.get(chest_ID=slug)
        chest.delete()
        return redirect('/')

'''
Search auth level
'''
class AuthLevelSearch(LoginRequiredMixin, generic.View):
    login_url = 'login/'

    def get(self, r):
        usr = Usr.objects.get(def_usr=r.user.id)
        chest = Chest.objects.get()

'''
Performs a validation, given a validator
'''
def validate(r, vname, fname):
    f = r.POST.get(fname)
    v = Validator.objects.get(name=vname)
    if v.validator is None and v.pattern is None:
        return True
    elif v.validator is None and v.pattern is not None:
        if image_extractor(v.pattern, f) is not False:
            return True
        else:
            return False
    elif v.validator is not None and v.pattern is not None:
        ex = image_extractor(v.pattern, f)
        if ex is not False:
            # post to the validator
            if v.identifier is not None:
                ctx = {
                    v.identifier: ex
                } 
                r = requests.post(v.validator, data=ctx)
                if r.status_code == 200:
                    return True
                else:
                    return False
            else:
                ctx = {
                    f.name: ex
                } 
                r = requests.post(v.validator, data=ctx)
                if r.status_code == 200:
                    return True
                else:
                    return False
        else:
            return False
    elif v.validator is not None and v.pattern is None:
        if v.identifier is not None:
            ctx = {
                v.identifier: f
            }
            r = requests.post(v.validator, data=ctx)
            if r.status_code == 200:
                return True
            else:
                return False
        else:
            ctx = {
                f.name: f
            }
            r = requests.post(v.validator, data=ctx)
            if r.status_code == 200:
                return True
            else:
                return False
    else:
        return False


'''
Creates a generic validator
'''
class ValidatorCreateView(generic.View):

    def get(self, r):
        # it'll return renderable create view
        pass

    def post(self, r):
        if r.POST.get('validator_name') is None:
            return redirect('/')
        Validator.objects.create(
            name = r.POST.get('validator_name'),
            validator = r.POST.get('validator'),
            pattern = r.POST.get('pattern'),
            identifier = r.POST.get('identifier')
        )

'''
User facing company ops grouping
'''
class GeneralCompany(generic.View, LoginRequiredMixin):

    login_url = "login/"

    def get(self, r):
        return render(r, "kycweb/corps.html")

    @login_required
    def search(r):
        st = r.POST.get("st") # search term
        cmps = Corporation.objects.filter(name__startswith = st) #comapnies
        len = cmps.count()
        ctx = {
            "cmps": cmps,
            "len": len
        }
        return render(r, "kycweb/corp.html", ctx)

    '''
    Add Permissions to specific chests 
    '''
    # renders the template for the addition request
    def add_perm_get(r):
        usr = Usr.objects.get(def_usr=r.user.id)
        chests_nf = Chest.objects.filter(created_by=usr)
        cmp = None
        try:
            cmp = Corporation.objects.get(key=r.GET.get("key"))
        except:
            cmp = None
        if cmp is not None:
            perms = ChestRegistry.objects.filter(corporation=cmp, chest__created_by=usr)
            if perms.count() > 0:
                chests = []
                for p in perms:
                    for c in chests_nf:
                        if p.chest.chest_ID == c.chest_ID:
                            pass
                        else:
                            chests.append(c)
            else:
                chests = chests_nf
        print(chests)
        len_ = len(chests)
        ctx = {
            "chests": chests,
            "len": len_,
            "cmp": cmp
        }

        return render(r, "kycweb/corp_add_perm.html", ctx)

    # actually add the perm on request
    def add_perm(r):
        usr = Usr.objects.get(def_usr=r.user.id)
        chests = corp = None
        try:
            chests = Chest.objects.get(chest_ID=r.POST.get("chest"))
        except:
            return JsonResponse({"error": "No such chest"})
        try:
            corp = Corporation.objects.get(key=r.POST.get("corp"))
        except:
            return JsonResponse({"error": "No such company"})

        ChestRegistry.objects.create(chest=chests, corporation=corp)
        return JsonResponse({"created": True})

    # render the view for removing company perm
    def rem_perm_get(r):
        usr = Usr.objects.get(def_usr=r.user.id)
        cmp = Corporation.objects.get(key=r.GET.get("cmp"))
        perms = ChestRegistry.objects.filter(corporation=cmp, chest__created_by=usr)
        len = perms.count()
        ctx = {
            "perms": perms,
            "len": len,
        }

        return render(r, "kycweb/corp_rem_perm.html", ctx)

    # actually remove the perm
    def rem_perm(r):
        perm = None
        pid = r.POST.get("perm")
        try:
            perm = ChestRegistry.objects.get(pk=pid)
        except:
            return JsonResponse({"deleted": True})

        perm.delete()
        return JsonResponse({"deleted": True})

    # remove all permissions for a corporation
    def rem_perm_all(r):
        cmp = r.POST.get("cmp")
        cmp = Corporation.objects.get(key=cmp)
        usr = Usr.objects.get(def_usr=r.user.id)
        perms = ChestRegistry.objects.filter(corporation=cmp, chest__created_by=usr)

        for p in perms:
            p.delete()

        return JsonResponse({"deleted": True})


'''
Non-user facing company ops grouping
for verifications/ dashboard
'''
class CompanyOperations(generic.View):
    login_url = 'login/'
    
    def get(self, r):
        corp = r.GET.get("key")
        if corp is None:
            return redirect('/companies/dash/open/')
        return render(r, 'kycweb/corp_dash.html', {'key': corp})

    @login_required
    def get_form(r):
        if r.user.is_staff:
            return render(r, 'registration/corp_login.html')
        else:
            return redirect('/')

    def post(self, r):
        corp = r.POST.get("key")
        name = r.POST.get("name")
        print(corp, name)
        try:
            Corporation.objects.get(key=corp, name=name)
        except:
            return JsonResponse({"error": "credentials don't exist"})

        return JsonResponse({"validated": True})


    def corp_info(r):
        corp = None
        try:
            corp = Corporation.objects.get(key=r.GET.get("key"))
        except:
            return JsonResponse({'key': 'None'})
        hosts = HostRegistry.objects.filter(corp=corp)
        key_uses = CorpKeyUses.objects.filter(host__corp=corp)

        ctx = {
            'corp':  corp,
            'hosts': hosts,
            'uses':  key_uses
        }

        return render(r, 'kycweb/corp_info.html', ctx)

    def toggle_key(r):
        corp = r.POST.get("key")
        cp = None
        try:
            cp = Corporation.objects.get(key=corp)
        except:
            return JsonResponse({'err': 'no such coorp'})
        
        if cp.enabled:
            cp.enabled = False
        else:
            cp.enabled = True

        return JsonResponse({'toggled': True})

    def new_host(r):
        cp = r.POST.get("key")
        hn = r.POST.get("hn")
        corp = None
        if cp is not None and hn is not None:
            try:
                corp = Corporation.objects.get(key=cp)
            except:
                return JsonResponse({'err': True, 'txt': "Error adding host, please reload page and try again"})
        
            # ping the host to check its validity
            resp = os.system("ping -c 1 " + hn)
            if resp == 0:
                nh = HostRegistry.objects.create(host=hn, corp=corp) # new host
                return render(r, "kycweb/host.html", {"h": nh})
            else:
                return JsonResponse({'err': True, 'txt': "Please enter a valid host name"})

        else:
            return JsonResponse({'err': True, 'txt': "Please enter a valid host name"})

    def rem_host(r):
        hid = r.POST.get("hid")
        if hid is not None:
            host = None
            try:
                host = HostRegistry.objects.get(pk=hid)
            except:
                return JsonResponse({"deleted": False, "txt": "couldn't find specified host"})

            host.delete()
            return JsonResponse({"deleted": True})

    def toggle_uses(r):
        val = r.POST.get('val')
        corp = Corporation.objects.get(key=r.POST.get('key'))
        if val == "true":
            uses = CorpKeyUses.objects.filter(host__corp=corp.id)
            hosts = HostRegistry.objects.filter(corp=corp.id)
            nr = []
            for u in uses:
                exists = False # if the used host exists in the allowed hosts
                for h in hosts:
                    if u.host == h:
                        exists = True
                if not exists:
                    nr.append(u)
            ctx = {
                'uses': nr,
            }
            return render(r, 'kycweb/uses.html', ctx)
        else:
            uses = CorpKeyUses.objects.filter(host__corp=corp.id)
            
            ctx = {
                'uses': uses
            }

            return render(r, 'kycweb/uses.html', ctx)
