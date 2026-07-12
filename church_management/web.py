import frappe

SPA_PATHS = ("/church_management",)


def set_no_store_headers(response=None, request=None):
	"""Send Cache-Control: no-store for the SPA shell page.

	Without an explicit Cache-Control header browsers heuristically cache the
	rendered HTML, which pins an old `?v=` asset URL; combined with nginx's
	1-year max-age on /assets this keeps serving a stale bundle after deploys.
	"""
	if response is None or request is None:
		return
	if request.path.rstrip("/") in SPA_PATHS:
		response.headers["Cache-Control"] = "no-store, must-revalidate"
