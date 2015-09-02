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
package org.datagator.api.client._backend;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.URISyntaxException;
import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;

import javax.net.ssl.SSLContext;

import com.fasterxml.jackson.core.JsonFactory;

import org.apache.commons.io.IOUtils;
import org.apache.http.HttpHost;
import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.client.AuthCache;
import org.apache.http.client.CredentialsProvider;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPatch;
import org.apache.http.client.protocol.HttpClientContext;
import org.apache.http.client.utils.URIBuilder;
import org.apache.http.conn.ssl.SSLConnectionSocketFactory;
import org.apache.http.impl.auth.BasicScheme;
import org.apache.http.impl.client.BasicAuthCache;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.ssl.SSLContexts;

import org.datagator.api.client.environ;

/**
 * Low-level HTTP client to back-end web services
 *
 * @author LIU Yu <liuyu@opencps.net>
 * @date 2015/09/01
 */
public class DataGatorService
{

    private static JsonFactory json = new JsonFactory();

    private final CloseableHttpClient http;
    private final HttpClientContext context;

    public DataGatorService()
    {
        super();
        // force TLSv1 protocol
        SSLConnectionSocketFactory ssl_factory = null;
        try {
            SSLContext ssl_context = SSLContexts.custom().build();
            ssl_factory = new SSLConnectionSocketFactory(ssl_context,
                new String[]{"TLSv1"}, null,
                SSLConnectionSocketFactory.getDefaultHostnameVerifier());
        } catch (KeyManagementException e) {
            e.printStackTrace();
        } catch (NoSuchAlgorithmException e) {
            e.printStackTrace();
        }
        this.http = HttpClients.custom().setSSLSocketFactory(ssl_factory)
            .setUserAgent(environ.DATAGATOR_API_USER_AGENT).build();
        this.context = HttpClientContext.create();
    }

    public DataGatorService(UsernamePasswordCredentials auth)
    {
        this();
        // attach credentials to context
        HttpHost host = new HttpHost(environ.DATAGATOR_API_HOST,
            environ.DATAGATOR_API_PORT, environ.DATAGATOR_API_SCHEME);
        AuthScope scope = new AuthScope(host.getHostName(), host.getPort());
        CredentialsProvider provider = new BasicCredentialsProvider();
        provider.setCredentials(scope, auth);
        this.context.setCredentialsProvider(provider);
        // enable preemptive (pro-active) basic authentication
        AuthCache cache = new BasicAuthCache();
        cache.put(host, new BasicScheme());
        this.context.setAuthCache(cache);
    }

    private static URI buildServiceURI(String endpoint)
        throws URISyntaxException
    {
        URI uri = new URIBuilder().setScheme(environ.DATAGATOR_API_SCHEME)
            .setHost(environ.DATAGATOR_API_HOST)
            .setPath(environ.DATAGATOR_API_URL_PREFIX + endpoint).build();
        return uri;
    }

    public CloseableHttpResponse get(String endpoint)
        throws URISyntaxException, IOException
    {
        URI uri = buildServiceURI(endpoint);
        HttpGet request = new HttpGet(uri);
        return http.execute(request, context);
    }

    public CloseableHttpResponse patch(String endpoint)
        throws URISyntaxException, IOException
    {
        URI uri = buildServiceURI(endpoint);
        HttpPatch request = new HttpPatch(uri);
        return http.execute(request, context);
    }

    public static void main(String[] args)
        throws Exception
    {
        java.util.logging.Logger.getLogger("org.apache.http.wire")
            .setLevel(java.util.logging.Level.FINEST);
        java.util.logging.Logger.getLogger("org.apache.http.headers")
            .setLevel(java.util.logging.Level.FINEST);

        System.setProperty("org.apache.commons.logging.Log",
            "org.apache.commons.logging.impl.SimpleLog");
        System.setProperty("org.apache.commons.logging.simplelog.showdatetime",
            "true");
        System.setProperty(
            "org.apache.commons.logging.simplelog.log.httpclient.wire",
            "debug");
        System.setProperty(
            "org.apache.commons.logging.simplelog.log.org.apache.http",
            "debug");
        System.setProperty(
            "org.apache.commons.logging.simplelog.log.org.apache.http.headers",
            "debug");

        UsernamePasswordCredentials auth = new UsernamePasswordCredentials(
            "Pardee", "");
        DataGatorService service = new DataGatorService(auth);

        InputStream stream = service.get("/").getEntity().getContent();

        // JsonParser parser = json.createParser(stream);
        IOUtils.copy(stream, System.out);
    }
}
