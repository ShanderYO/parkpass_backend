from base.views import PartnerRequestAPIView
from parkings.views import GetParkingViewMixin


class GetPartnerParkingView(GetParkingViewMixin, PartnerRequestAPIView):
    pass


class GetPartnerTariffParkingView(PartnerRequestAPIView):
    pass

class GetPartnerAvailableParkingsView(PartnerRequestAPIView):
    pass

class GetPartnerParkingCardDebt(PartnerRequestAPIView):
    pass

class InitPartnerPayDebt(PartnerRequestAPIView):
    pass

class GetPartnerCardSessionStatus(PartnerRequestAPIView):
    pass
