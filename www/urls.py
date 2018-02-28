# -*- coding: utf-8 -*-

"""URL definitions of the application. Regex based URLs are mapped to their
class handlers.
"""

from app.controllers.main_handler import Index, Logout
from app.controllers.api import Location, LocationChildren, SubcountyLocations
from app.controllers.api import DistrictFacilities, LocationFacilities, FacilityReporters
from app.controllers.api2 import LocationsEndpoint, ReportersXLEndpoint
from app.controllers.api2 import CreateFacility
from app.controllers.api3 import MatchSubcounty
from app.controllers.api4 import ReportersAPI
from app.controllers.reporters_handler import Reporters
from app.controllers.users_handler import Users
from app.controllers.groups_handler import Groups
from app.controllers.dashboard_handler import Dashboard
from app.controllers.auditlog_handler import AuditLog
from app.controllers.forgotpass_handler import ForgotPass
from app.controllers.facilities_handler import Facilities
from app.controllers.downloads_handler import Downloads
from app.controllers.adminunits_handler import AdminUnits
from app.controllers.fsync_handler import FSync
from app.controllers.bulkupload_handler import BulkUpload

URLS = (
    r'^/', Index,
    r'/adminunits', AdminUnits,
    r'/downloads', Downloads,
    r'/reporters', Reporters,
    r'/reportersupload', ReportersAPI,
    r'/bulkupload', BulkUpload,
    r'/facilities', Facilities,
    r'/auditlog', AuditLog,
    r'/fsync', FSync,
    r'/dashboard', Dashboard,
    r'/users', Users,
    r'/groups', Groups,
    r'/logout', Logout,
    r'/forgotpass', ForgotPass,
    r'/create', CreateFacility,
    r'/subcountysync', MatchSubcounty,
    # API stuff follows
    r'/api/v1/loc_children/(\d+)/?', LocationChildren,
    r'/api/v1/district_facilities/(\d+)/?', DistrictFacilities,
    r'/api/v1/facility_reporters/(\d+)/?', FacilityReporters,
    r'/api/v1/loc_facilities/(\d+)/?', LocationFacilities,
    r'/api/v1/location/(\d+)/?', Location,
    r'/api/v1/subcountylocations/(\d+)/?', SubcountyLocations,
    r'/api/v1/locations_endpoint/(\w+)/?', LocationsEndpoint,
    r'/api/v1/reporters_xlendpoint', ReportersXLEndpoint,
)
