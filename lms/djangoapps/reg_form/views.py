from django.shortcuts import render, HttpResponse

# Create your views here.
def ajaxform(request):
	if request.method == 'POST':

		usertype = request.POST['usertype']

		return HttpResponse("registration/reg_usertype.html",{'usertype': usertype}
    	)