from django.http import request
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .forms import UserForm, UsrForm
from .models import ChestRegistry, Chest, Usr, FileInstances, HitsRegistry

LIMIT = 100000000

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
    n_chests = n_hits = n_size = 0
    dng = False
    chests = Chest.objects.filter(created_by=r.user.id)
    n_hits = HitsRegistry.objects.filter(usr__id=r.user.id).count()
    n_chests = chests.count()
    if n_chests>1:
        for i in chests:
            n_size += int(i.chest_size)
    elif n_chests == 1:
        n_size = int(chests.chest_size)
    else:
        n_size = n_size
    if (n_size/LIMIT)*100 <= 5 and (n_size/LIMIT)*100 > 0:
        dng = True
    print(dng)
    return render(r, 'kycweb/dash.html', {'chests':chests, 
                                          'n_chests':n_chests, 
                                          'size':n_size, 
                                          'lim':LIMIT/1000000,
                                          'dng': dng,
                                          'n_hits': n_hits
                                          })
