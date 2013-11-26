#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2013 Unicon Pte. Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, with_statement

try:
    import setuptools
    from setuptools import setup
except ImportError:
    setuptools = None
    from distutils.core import setup

kwargs = {}

if setuptools is not None:
    kwargs["install_requires"] = [
        "tornado==3.1.1",
        "pika==0.9.13",
    ]

setup(
    name = "funnel",
    version = "0.9.0",
    packages = ["funnel"],
    author = "Unicon Pte. Ltd.",
    author_email = "",
    url = "",
    license = "http://www.apache.org/licenses/LICENSE-2.0",
    description = "Funnel is a simple asynchronous job queue framework.",
    **kwargs
)
