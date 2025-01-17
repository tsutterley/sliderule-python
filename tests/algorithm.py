#!/usr/bin/env python
u"""
algorithm.py
"""
#
# Imports
#
import sys
import logging
import time

import pandas as pd
import numpy as np
import math

import matplotlib.pyplot as plt
import cartopy

from sliderule import icesat2

#
# SlideRule Processing Request
#
def algoexec(resource, asset):

    # Build ATL06 Request
    parms = { "cnf": 4,
              "ats": 20.0,
              "cnt": 10,
              "len": 40.0,
              "res": 20.0,
              "maxi": 1 }

    # Request ATL06 Data
    perf_start = time.perf_counter()
    process_start = time.process_time()
    gdf = icesat2.atl06(parms, resource, asset)
    perf_stop = time.perf_counter()
    process_stop = time.process_time()
    perf_duration = perf_stop - perf_start
    process_duration = process_stop - process_start

    # Check Results #
    if len(gdf["h_mean"]) != 622423:
        print("Failed atl06-sr algorithm test - incorrect number of points returned: ", len(gdf["h_mean"]))
    else:
        print("Passed atl06-sr algorithm test")

    # Return DataFrame
    print("Completed in {:.3f} seconds of wall-clock time, and {:.3f} seconds of processing time". format(perf_duration, process_duration))
    print("Reference Ground Tracks: {} to {}".format(min(gdf["rgt"]), max(gdf["rgt"])))
    print("Cycle: {} to {}".format(min(gdf["cycle"]), max(gdf["cycle"])))
    print("Retrieved {} points from SlideRule".format(len(gdf["h_mean"])))
    return gdf

#
# ATL06 Read Request
#
def expread(resource, asset):

    # Read ATL06 Data
    heights     = icesat2.h5("/gt1r/land_ice_segments/h_li",        resource, asset)
    delta_time  = icesat2.h5("/gt1r/land_ice_segments/delta_time",  resource, asset)

    # Build Dataframe of SlideRule Responses
    df = pd.DataFrame(data=list(zip(heights, delta_time)), index=delta_time, columns=["h_mean", "delta_time"])
    df['time'] = pd.to_datetime(np.datetime64(icesat2.ATLAS_SDP_EPOCH) + (delta_time * 1000000.0).astype('timedelta64[us]'))

    # Filter Bad Elevations #
    df = df[df["h_mean"] < 4000]

    # Check Results #
    if len(df.values) != 117080:
        print("Failed h5 retrieval test - insufficient points returned: ", len(df.values))
    else:
        print("Passed h5 retrieval test")

    # Return DataFrame
    print("Retrieved {} points from ATL06".format(len(heights)))
    return df

#
# ATL03 Photon Cloud Request
#
def phread(resource, asset, region):

    # Build ATL06 Request
    parms = { "poly": region,
              "cnf": icesat2.CNF_SURFACE_HIGH,
              "pass_invalid": True,
              "atl08_class": ["atl08_noise", "atl08_ground", "atl08_canopy", "atl08_top_of_canopy", "atl08_unclassified"],
              "ats": 20.0,
              "cnt": 10,
              "len": 40.0,
              "res": 20.0,
              "maxi": 1 }

    # Request ATL06 Data
    perf_start = time.perf_counter()
    process_start = time.process_time()
    gdf = icesat2.atl03s(parms, resource, asset, track=1)
    perf_stop = time.perf_counter()
    process_stop = time.process_time()
    perf_duration = perf_stop - perf_start
    process_duration = process_stop - process_start

    # Return DataFrame
    print("Completed in {:.3f} seconds of wall-clock time, and {:.3f} seconds of processing time". format(perf_duration, process_duration))
    print("Reference Ground Tracks: {} to {}".format(min(gdf["rgt"]), max(gdf["rgt"])))
    print("Cycle: {} to {}".format(min(gdf["cycle"]), max(gdf["cycle"])))
    print("Retrieved {} points from SlideRule".format(len(gdf["height"])))
    return gdf

#
# Plot Actual vs Expected
#
def plotresults(act, exp, ph, region):

    # Build Box
    box_lon = [coord["lon"] for coord in region]
    box_lat = [coord["lat"] for coord in region]

    # Sort Results by Time
    act = act.sort_values(by=['delta_time'])

    # Create Plot
    fig = plt.figure(num=None, figsize=(16, 10))

    # Plot Ground Tracks
    ax1 = plt.subplot(131,projection=cartopy.crs.SouthPolarStereo())
    ax1.gridlines()
    ax1.set_title("Ground Tracks")
    ax1.plot(act.geometry.x, act.geometry.y, linewidth=0.5, color='r', zorder=2, transform=cartopy.crs.Geodetic())
    ax1.plot(box_lon, box_lat, linewidth=1.5, color='b', zorder=3, transform=cartopy.crs.Geodetic())
    ax1.add_feature(cartopy.feature.LAND, zorder=0, edgecolor='black')
    ax1.add_feature(cartopy.feature.LAKES)
    ax1.set_xmargin(1.0)
    ax1.set_ymargin(1.0)

    # Plot Elevations
    ax2 = plt.subplot(132)
    ax2.set_title("Along Track Elevations")
    act_gt1r = act[act["gt"] == icesat2.GT1R]
    ax2.scatter(act_gt1r["time"].values, act_gt1r["h_mean"].values, s=0.5, color='b', zorder=3)
    ax2.scatter(exp["time"].values, exp["h_mean"].values, s=1.5, color='g', zorder=2)

    # Plot Photon Cloud
    ax3 = plt.subplot(133)
    ax3.set_title("Photon Cloud")
    ph_gt1r = ph[ph["pair"] == icesat2.RIGHT_PAIR]
    colormap = np.array(['c','b','g','g','y']) # noise, ground, canopy, top of canopy, unclassified
    ax3.scatter(ph_gt1r["time"], ph_gt1r["height"].values, c=colormap[ph_gt1r["info"]], s=1.5)
    act_gt1r = act_gt1r[(act_gt1r.geometry.y > min(box_lat)) & (act_gt1r.geometry.y < max(box_lat))]
    act_gt1r = act_gt1r[(act_gt1r.geometry.x > min(box_lon)) & (act_gt1r.geometry.x < max(box_lon))]
    ax3.scatter(act_gt1r["time"], act_gt1r["h_mean"].values, color='r', s=0.5)

    # Show Plot
    fig.tight_layout()
    plt.show()

###############################################################################
# MAIN
###############################################################################

if __name__ == '__main__':

    url = ["127.0.0.1"]
    asset = "atlas-local"
    resource = "20181019065445_03150111_004_01"
    photon_cloud_region = [
        { "lat": -80.75, "lon": -70.00 },
        { "lat": -81.00, "lon": -70.00 },
        { "lat": -81.00, "lon": -65.00 },
        { "lat": -80.75, "lon": -65.00 },
        { "lat": -80.75, "lon": -70.00 }
    ]

    # configure logging
    logging.basicConfig(level=logging.INFO)

    # Set URL #
    if len(sys.argv) > 1:
        url = sys.argv[1]
        asset = "nsidc-s3"

    # Set Asset #
    if len(sys.argv) > 2:
        asset = sys.argv[2]

    # Bypass service discovery if url supplied
    if len(sys.argv) > 3:
        if sys.argv[3] == "bypass":
            url = [url]

    # Set Resource #
    if len(sys.argv) > 4:
        resource = sys.argv[4]

    # Initialize Icesat2 Package #
    icesat2.init(url, True)

    # Execute SlideRule Algorithm
    act = algoexec("ATL03_"+resource+".h5", asset)

    # Read ATL06 Expected Results
    exp = expread("ATL06_"+resource+".h5", asset)

    # Read ATL03 Photon Cloud
    ph = phread("ATL03_"+resource+".h5", asset, photon_cloud_region)

    # Plot Actual vs. Expected
    plotresults(act, exp, ph, photon_cloud_region)