from app.services.deduplication import fingerprint


def make(**kw):
    from app.schemas.job import NormalizedJob

    base = dict(external_id="1", source="greenhouse", company="Example Inc.", title="Software Engineer", location="New York, NY")
    base.update(kw)
    return NormalizedJob(**base)


def test_same_job_from_two_sources_shares_a_fingerprint():
    a = make(source="greenhouse", external_id="1", company="Example Inc.")
    b = make(source="lever", external_id="abc", company="Example, LLC")
    assert fingerprint(a) == fingerprint(b)


def test_title_decorations_do_not_change_the_fingerprint():
    a = make(title="Software Engineer")
    b = make(title="Software Engineer (New Grad)")
    assert fingerprint(a) == fingerprint(b)


def test_different_location_is_a_different_job():
    assert fingerprint(make(location="New York, NY")) != fingerprint(make(location="Austin, TX"))


def test_different_company_is_a_different_job():
    assert fingerprint(make(company="Example Inc.")) != fingerprint(make(company="Other Inc."))
