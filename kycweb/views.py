from django.http import request
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .forms import UserForm, UsrForm, FileForm
from .models import ChestRegistry, Chest, Usr, FileInstances, HitsRegistry, User
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import FileSystemStorage
import pathlib, os, sys, pytesseract, pdf2image, PIL, io, numpy, re, requests, json
from PIL import ImageEnhance, ImageOps

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


'''
Loads chest data & information and renders chests UI
'''
@login_required
def chests(r):
    n_chests = n_hits = n_size = 0
    dng = False
    usr = Usr.objects.get(def_usr=r.user.id)
    chests = Chest.objects.filter(created_by=usr.id)
    n_hits = HitsRegistry.objects.filter(usr__id=r.user.id).count()
    n_chests = chests.count()
    if n_chests>0:
        for i in chests:
            n_size += sum(os.path.getsize(f) for f in os.listdir(i.chest_dir) if os.path.isfile(f))
    else:
        n_size = n_size
    if (n_size/LIMIT)*100 <= 5 and (n_size/LIMIT)*100 > 0:
        dng = True
    return render(r, 'kycweb/chests.html', {'chests':chests, 
                                          'n_chests':n_chests, 
                                          'size':n_size, 
                                          'lim':LIMIT/1000000,
                                          'dng': dng,
                                          'n_hits': n_hits
                                          })

'''
Check file Type
'''
def file_type(ext):
    types = {"image": ['.jpg', '.gif', '.jpeg', '.png', '.tiff', '.bmp'],
                "video": ['.webm', '.mpeg4', '.3gpp', '.mov', '.avi', '.mpegps', '.wmv', '.flv'],
                "document": ['.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt', '.pdf'],
                "code": ['.c', '.cpp', '.py', '.java', '.html', '.css']}
    for key in types:
        if ext in types[key]:
            return key
'''
Creates new file instance/ uploads it
'''
def new_file(c, r, fn=None):

    if fn is not None:
        fa = r.FILES.get(fn)
        up = c.chest_dir + '/' + fa.name
        fs = FileSystemStorage(location=c.chest_dir)
        fs.save(fa.name, fa)
        ft = pathlib.Path(fa.name).suffix
        FileInstances.objects.create(chest=c, upload_path=up, file_type=file_type(ft))
        return True
    else:
        for ft in r.FILES:
            fa = r.FILES.get(ft)
            up = c.chest_dir + '/' + fa.name
            fs = FileSystemStorage(location=c.chest_dir)
            fs.save(fa.name, fa)
            ft = pathlib.Path(fa.name).suffix
            FileInstances.objects.create(chest=c, upload_path=up, file_type=file_type(ft))
        return True

'''
Extract and RE pattern from image if it can
'''
def image_extractor(ptn, fa):
    fa.seek(0)
    fc = fa.read()
    ft = file_type(pathlib.Path(fa.name).suffix)
    if ft == "document":
        pages = pdf2image.convert_from_bytes(fc)
        dct = ""
        for pg in pages:
            pg = pg.convert('RGBA')
            data = numpy.array(pg)
            red, green, blue, alpha = data.T
            black_to_gray = (red > 140) & (blue > 130) & (green > 128)
            data[..., :-1][black_to_gray.T] = (255, 255, 255) 
            pg = PIL.Image.fromarray(data)
            txt = pytesseract.image_to_string(pg)
            dct = dct + txt + "\n"    
        idn = re.search(ptn, dct)
        if idn:
            return idn.group()
        else:
            return False
    if ft == "image":
        img = PIL.Image.open(io.BytesIO(fc))
        img = img.convert('RGBA')
        data = numpy.array(img)
        red, green, blue, alpha = data.T
        black_to_gray = (red > 140) & (blue > 130) & (green > 128)
        data[..., :-1][black_to_gray.T] = (255, 255, 255) 
        img = PIL.Image.fromarray(data)
        txt = pytesseract.image_to_string(img)
        idn = re.search(ptn, txt)
        if idn:
            return idn.group()
        else:
            return False

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
    if idn:
        headers = {
            "Authentication": str(get_bearer_token())
        }
        data = {
            "id": "34938447"
        }
        r = requests.post("https://sandbox.jengahq.io/identity-test/v2/token", headers=headers, data=data).json()
        print(r)
        ctx = {
            'verified': True,
        }
        return JsonResponse(ctx)
    else:
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
    if idn:
        print(idn)
        ctx = {
            'verified': True,
        }
        return JsonResponse(ctx)
    else:
        ctx = {
            'verified': True,
        }
        return JsonResponse(ctx)

'''
New Banking auth instance. This 
only exists as an abstract 'Model',
and extention of the Chest Model 
'''
class BankingChestCreateView(LoginRequiredMixin, generic.View):
    pass

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
        usr = Usr.objects.get(def_usr=r.user.id)
        chest_type = r.POST.get('chest-types')
        chest = Chest.objects.create(chest_name=r.POST.get('chest-name'), chest_size=0, created_by=usr)
        nfls = int(r.POST.get('size-flag'))
        if chest_type == "oth":
            for i in range(0, nfls):
                new_file(chest, r)
        return redirect("/")