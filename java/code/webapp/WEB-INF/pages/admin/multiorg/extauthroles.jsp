<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<%@ taglib uri="http://rhn.redhat.com/rhn" prefix="rhn" %>
<%@ taglib uri="http://rhn.redhat.com/tags/list" prefix="rl" %>
<%@ taglib uri="http://struts.apache.org/tags-bean" prefix="bean" %>
<%@ taglib uri="http://struts.apache.org/tags-html" prefix="html" %>

<html:html>
    <head>
    </head>
    <body>
    <rhn:toolbar base="h1" icon="header-organisation"
            creationUrl="ExtGroupDetails.do"
            creationType="extgroup"
            iconAlt="info.alt.img">
        <bean:message key="org.allusers.title1" />
    </rhn:toolbar>

<div class="panel-heading">
    <h4><bean:message key="extgroup.jsp.header"/></h4>
</div>
<div class="panel-body">
    <p><bean:message key="extgroups.jsp.summary"/></p>
</div>

<rl:listset name="groupRolesSet">
<rhn:csrf />
<rhn:submitted />

  <rl:list width="100%"
         styleclass="list"
         emptykey="extauth.jsp.noGroups" >

    <rl:column bound="false"
               sortable="true"
               headerkey="extgrouplist.jsp.name"
               attr="label"
               filterattr="label">
        <a href="/rhn/admin/multiorg/ExtGroupDetails.do?gid=${current.id}">
            <c:out value="${current.label}" escapeXml="true" />
        </a>
    </rl:column>

    <rl:column attr="roleNames"
               bound="true"
               headerkey="userdetails.jsp.roles" />
  </rl:list>
</rl:listset>


</body>
</html:html>
