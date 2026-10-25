"""The setup helpers that turn what a student types into Terraform inputs."""

import pytest

import course


@pytest.mark.parametrize(
    ("typed", "expected"), [("xyz1234", "xyz1234"), (" QFX2034 ", "qfx2034"), ("pabloprof", "pabloprof")]
)
def test_student_id_is_normalized(typed, expected):
    assert course.normalize_student_id(typed) == expected


@pytest.mark.parametrize("typed", ["abc1234", "ABC1234"])
def test_student_id_rejects_the_placeholder(typed):
    with pytest.raises(ValueError, match="with your own NetID"):
        course.normalize_student_id(typed)


@pytest.mark.parametrize("typed", ["1abc", "ab", "net-id", "toolongnetid123", ""])
def test_student_id_rejects_invalid_ids(typed):
    with pytest.raises(ValueError, match="is not valid"):
        course.normalize_student_id(typed)


GROUPS = ["QFX2034_resourcegroup", "nwfy26qa_resourcegroup", "pablo_professor"]


def test_class_group_is_found_from_the_netid():
    assert course.pick_resource_group("qfx2034", "", True, GROUPS) == ("QFX2034_resourcegroup", False)


def test_named_group_keeps_its_azure_spelling():
    assert course.pick_resource_group("pabloprof", "PABLO_PROFESSOR", False, GROUPS) == ("pablo_professor", False)


def test_missing_named_group_suggests_the_closest_name():
    with pytest.raises(ValueError, match=r"was not found.*Did you mean nwfy26qa_resourcegroup"):
        course.pick_resource_group("nwfy26qa", "nwfy26qa_resourcgroup", False, GROUPS)


def test_missing_named_group_lists_what_exists():
    with pytest.raises(ValueError, match=r"Groups you can see: .*pablo_professor"):
        course.pick_resource_group("xyz1234", "other", False, GROUPS)


def test_without_a_class_group_terraform_creates_one():
    assert course.pick_resource_group("xyz1234", "", True, GROUPS) == ("", True)
    assert course.pick_resource_group("xyz1234", "rg-custom", True, GROUPS) == ("rg-custom", True)
