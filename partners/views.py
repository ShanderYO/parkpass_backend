from base.views import PartnerRequestAPIView
from parkings.views import GetParkingViewMixin, GetParkingViewListMixin
from rps_vendor.views import GetParkingCardDebtMixin, InitPayDebt, GetCardSessionStatusMixin, InitWebPayDebt


class GetPartnerParkingView(GetParkingViewMixin, PartnerRequestAPIView):
    pass


class GetPartnerAvailableParkingsView(PartnerRequestAPIView):
    def get(self, request, *args, **kwargs):
        if not request.GET.get("lt_lat", None) and not request.GET.get("lt_lon", None) \
                and not request.GET.get("rb_lat", None) and not request.GET.get("rb_lon", None):
            get_params = request.GET.copy()
            get_params["lt_lat"] = 90
            get_params["lt_lon"] = -180
            get_params["rb_lat"] = -90
            get_params["rb_lon"] = 180
            request.GET = get_params

        mixin = GetParkingViewListMixin()
        return mixin.get(request, *args, **kwargs)


class GetPartnerParkingCardDebt(GetParkingCardDebtMixin, PartnerRequestAPIView):
    pass


class InitPartnerPayDebt(InitPayDebt, PartnerRequestAPIView):
    pass

class InitPartnerWebPayDebt(InitWebPayDebt, PartnerRequestAPIView):
    pass

class GetPartnerCardSessionStatus(GetCardSessionStatusMixin, PartnerRequestAPIView):
    pass
