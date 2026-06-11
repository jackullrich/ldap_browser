import json

from mythic_container.CustomBrowserBase import *
from mythic_container.MythicGoRPC.send_mythic_rpc_custombrowser_search import *
from mythic_container.MythicGoRPC.send_mythic_rpc_file_create import *
from bhopengraph.OpenGraph import OpenGraph
from bhopengraph.Node import Node
from bhopengraph.Edge import Edge
from bhopengraph.Properties import Properties


async def export_ldap_browser(self, message: ExportFunctionMessage) -> ExportFunctionMessageResponse:
    print(f"incoming export request: {message.to_json()}")
    return ExportFunctionMessageResponse(Success=True, CompletionMessage="Planned future support for BloodHound OpenGraph.\nIf interested, help out :)")
    mythicTree = await SendMythicRPCCustomBrowserSearch(MythicRPCCustomBrowserSearchMessage(
        OperationID=message.OperationID,
        GetAllMatchingChildren=True,
        SearchCustomBrowser=MythicRPCCustomBrowserSearchData(
            TreeType=message.TreeType,
            FullPath=message.Path,
            Host=message.Host,
            CallbackGroup=message.CallbackGroup,
        )
    ))
    if mythicTree.Success:
        graph = OpenGraph(source_kind="Base")
        distinguishedNameMap = {}
        for x in mythicTree.CustomBrowser:
            if 'objectsid' in x.Metadata:
                kinds = ["ADBase"]
                if 'objectclass' in x.Metadata and "computer" in x.Metadata['objectclass']:
                    kinds.append("Computer")
                elif 'objectclass' in x.Metadata and "user" in x.Metadata['objectclass']:
                    kinds.append("User")
                elif 'objectclass' in x.Metadata and "group" in x.Metadata['objectclass']:
                    kinds.append("Group")
                elif 'objectclass' in x.Metadata and "organizationalUnit" in x.Metadata['objectclass']:
                    kinds.append("OU")
                elif 'objectclass' in x.Metadata and "domain" in x.Metadata['objectclass']:
                    kinds.append("Domain")
                graph.add_node(Node(
                    id=x.Metadata['objectsid'],
                    kinds=kinds,
                    properties=Properties(
                        **x.Metadata
                    )
                ))
                if 'distinguishedname' in x.Metadata:
                    distinguishedNameMap[x.Metadata['distinguishedname']] = x.Metadata['objectsid']
        # now to create edges
        for x in mythicTree.CustomBrowser:
            if 'memberof' in x.Metadata and 'objectsid' in x.Metadata:
                for member in x.Metadata['memberof']:
                    if member in distinguishedNameMap:
                        graph.add_edge(Edge(
                            kind="MemberOf",
                            start_node=x.Metadata['objectsid'],
                            end_node=distinguishedNameMap[member],
                        ))
            if 'member' in x.Metadata and 'objectsid' in x.Metadata:
                for member in x.Metadata['member']:
                    if member in distinguishedNameMap:
                        graph.add_edge(Edge(
                            kind="MemberOf",
                            end_node=x.Metadata['objectsid'],
                            start_node=distinguishedNameMap[member],
                        ))
        if graph.get_node_count() > 0 and graph.get_edge_count() > 0:
            graphDict = graph.export_to_dict()
            fileCreateResp = await SendMythicRPCFileCreate(MythicRPCFileCreateMessage(
                OperationID=message.OperationID,
                OperatorID=message.OperatorID,
                FileContents=json.dumps(graphDict).encode(),
                Filename="ldap_browser-dump.json",
            ))
            if not fileCreateResp.Success:
                logger.info(f"Failed to create file: {fileCreateResp.Error}")
        else:
            logger.info(f"No nodes added to graph, not creating a file")
        #logger.info(f"Successfully searched: {[x.to_json() for x in mythicTree.CustomBrowser]}")
    else:
        logger.info(f"Failed to search: {mythicTree.Error}")
    return ExportFunctionMessageResponse(Success=True, CompletionMessage="Creating file in future support of OpenGraph support, but no edges added currently")

class LdapBrowser(CustomBrowser):
    name = "ldap_browser"
    description = "A browser for LDAP information."
    author = "@its_a_feature_"
    semver = "0.0.1"
    indicate_partial_listing = False
    show_current_path = True
    path_separator = ","
    row_actions = [
        CustomBrowserRowAction(
            Name="Set Attribute",
            UIFeature="ldap_browser:set_attribute",
            SupportsFile=True,
            SupportsFolder=True,
            OpenDialog=True,
            GetConfirmation=False,
            Icon="fa-pen-to-square",
            Color="warning"
        )
    ]
    columns = [
        CustomBrowserTableColumn(
            Key="ldap_type",
            Name="Type",
            FillWidth=False,
            Width=90,
            DisableSort=False,
            DisableFilterMenu=False,
            DisableDoubleClick=False,
            ColumnType=CustomBrowserTableColumnType.String
        ),
        CustomBrowserTableColumn(
            Key="display_name",
            Name="Display",
            FillWidth=True,
            Width=160,
            DisableSort=False,
            DisableFilterMenu=False,
            DisableDoubleClick=False,
            ColumnType=CustomBrowserTableColumnType.String
        ),
        CustomBrowserTableColumn(
            Key="samaccountname",
            Name="Account",
            FillWidth=False,
            Width=140,
            DisableSort=False,
            DisableFilterMenu=False,
            DisableDoubleClick=False,
            ColumnType=CustomBrowserTableColumnType.String
        ),
        CustomBrowserTableColumn(
            Key="description",
            Name="Description",
            FillWidth=True,
            Width=220,
            DisableSort=False,
            DisableFilterMenu=False,
            DisableDoubleClick=False,
            ColumnType=CustomBrowserTableColumnType.String
        ),
        CustomBrowserTableColumn(
            Key="dn",
            Name="DN",
            FillWidth=True,
            Width=360,
            DisableSort=False,
            DisableFilterMenu=False,
            DisableDoubleClick=False,
            ColumnType=CustomBrowserTableColumnType.String
        )
    ]
    default_visible_columns = [
        "Type", "Display", "Account", "Description", "DN"
    ]
    extra_table_inputs = [
        CustomBrowserExtraTableTaskingInput(
            Name="query",
            DisplayName="Query",
            Description="LDAP Query",
            Required=True,
        ),
        CustomBrowserExtraTableTaskingInput(
            Name="attributes",
            DisplayName="Attributes",
            Description="Comma separated list of attributes to fetch",
        )
    ]
    export_function = export_ldap_browser



