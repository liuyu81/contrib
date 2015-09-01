/*
 * Copyright 2015 by University of Denver <http://pardee.du.edu/>
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * resource bundle facet for the client package
 *
 * @author LIU Yu <liuyu@opencps.net>
 * @date 2015/09/01
 */

package org.datagator.api.client;

import java.util.MissingResourceException;
import java.util.ResourceBundle;

public final class environ
{
	private static final ResourceBundle RESOURCE_BUNDLE = ResourceBundle
	    .getBundle("org.datagator.api.client");

	private static final String get(String key)
	{
		try {
			return RESOURCE_BUNDLE.getString(key);
		} catch (MissingResourceException e) {
			return '!' + key + '!';
		}
	}

	public static final String DATAGATOR_API_CLIENT_VERSION = get(
	    "DATAGATOR_API_CLIENT_VERSION");

	public static final String DATAGATOR_API_HOST = get("DATAGATOR_API_HOST");

	public static final String DATAGATOR_API_SCHEME = get(
	    "DATAGATOR_API_SCHEME");

	public static final int DATAGATOR_API_PORT = Integer
	    .parseInt(get("DATAGATOR_API_PORT"));

	public static final String DATAGATOR_API_VERSION = get(
	    "DATAGATOR_API_VERSION");

	// relative URI (relative to site root)
	public static final String DATAGATOR_API_URL_PREFIX = String
	    .format("/api/%s", DATAGATOR_API_VERSION);

	// absolute URI
	public static final String DATAGATOR_API_URL = String.format("%s://%s%s",
	    DATAGATOR_API_SCHEME, DATAGATOR_API_HOST, DATAGATOR_API_URL_PREFIX);

	// user agent
	public static final String DATAGATOR_API_USER_AGENT = String
	    .format("datagator-api-client (java/%s)", DATAGATOR_API_CLIENT_VERSION);
}
