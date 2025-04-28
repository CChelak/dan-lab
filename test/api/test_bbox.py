#!/usr/bin/env python3

"""Test the bounding box functions and objects
"""

from unittest import TestCase, main

from shapely import Point

from danlab.api.bbox import create_bbox_string, doctor_bbox_latlon_string

class TestCreateBboxString(TestCase):
    """Test create_bbox_string() function
    """
    def test_no_list(self):
        """Test that an error occurs when a list of points is not given
        """
        one_point = Point(-110, 50) # Somewhere near the AB/SK border
        with self.assertRaises(ValueError):
            create_bbox_string(region_coord=one_point)

    def test_one_point(self):
        """Test that an error occurs when a list contains 0-1 points
        """
        with self.assertRaises(ValueError):
            create_bbox_string([]) # An empty string should cause an error

        with self.assertRaises(ValueError):
            create_bbox_string([Point(1,2),])

    def test_bad_point_type(self):
        """Test that an error occurs when a list contains something other than a Point type
        """
        with self.assertRaises(ValueError):
            create_bbox_string([1,2,3,4])

    def test_reorder_min_max(self):
        """Reorder the min and max longitude/latitude in output
        """
        expected_output_1 = "-113.1,49.5,-113.0,50.1"
        unordered_1 = [Point(-113, 50.1), Point(-113.1, 49.5)]
        self.assertEqual(create_bbox_string(unordered_1), expected_output_1)

        expected_output_2 = "-112.8,52.1,-112.7,52.2"
        unordered_2 = [Point(-112.7, 52.1), Point(-112.8, 52.2)]
        self.assertEqual(create_bbox_string(unordered_2), expected_output_2)

    def test_extra_lon_lat(self):
        """See if you can create a bounding box string from a larger collection of LatLon
        """
        orig_input = [Point(10, 20), Point(-14, -88.3), Point(100.0, 45), Point(-48.1, 77.7)]
        expected_output = "-48.1,-88.3,100.0,77.7"

        self.assertEqual(create_bbox_string(orig_input), expected_output)

class TestDoctorBBoxLatlonString(TestCase):
    """Test the doctor_bbox_latlon_string function
    """
    def test_insufficient_input(self):
        """Give it an insufficient number of entries, and show an error
        """
        with self.assertRaises(ValueError):
            doctor_bbox_latlon_string("")
        with self.assertRaises(ValueError):
            doctor_bbox_latlon_string("11")
        with self.assertRaises(ValueError):
            doctor_bbox_latlon_string("112,30")
        with self.assertRaises(ValueError):
            doctor_bbox_latlon_string("-110,60,-130")
        with self.assertRaises(ValueError):
            doctor_bbox_latlon_string("-117,60,-119,")

    def test_number_inputs(self):
        """Give inputs that are not numbers, and show error
        """
        with self.assertRaises(ValueError):
            doctor_bbox_latlon_string("1,2,3,notanum")

    def test_original_input_format(self):
        """Ensure that the format of the numbers are preserved, despite the order possibly changing
        """
        orig_input = "40.00,030.01,-20.01,.4"
        expected_output = "-20.01,.4,40.00,030.01"

        self.assertEqual(doctor_bbox_latlon_string(orig_input), expected_output)

    def test_extra_lon_lat(self):
        """Given a longer list of longitude latitude coordinates, form a bounding box of min/max
        """
        orig_input = "70.3,40.0,119.3,0.0,55.2,-45.8,-111.11,22.4"
        expected_output = "-111.11,-45.8,119.3,40.0"

        self.assertEqual(doctor_bbox_latlon_string(orig_input), expected_output)

    def test_no_edit(self):
        """Give a totally clean and expected input and see that nothing changes
        """
        orig_input = "30.2,-110.34,34.5,-109.08"

        self.assertEqual(doctor_bbox_latlon_string(orig_input), orig_input)


if __name__ == '__main__':
    main()
