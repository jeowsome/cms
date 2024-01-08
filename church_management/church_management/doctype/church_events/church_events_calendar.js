frappe.views.calendar['Church Events'] = {
    field_map: {
        start: 'event_date',
        end: 'until',
        id: 'name',
        allDay: 'to_announce',
        title: 'subject',
        status: 'status',
        color: 'color'
    },
    style_map: {
        Upcoming: 'info',
        Done: 'success',
        Moved: 'warning',
        Cancelled: 'danger'
    },
    order_by: 'event_date',
    get_events_method: 'church_management.church_management.doctype.church_events.church_events.get_events'
}