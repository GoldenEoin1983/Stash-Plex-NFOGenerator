# Plugins

Stash supports plugins that can do the following:

- perform custom tasks when triggered by the user from the Tasks page
- perform custom tasks when triggered from specific events
- add custom CSS to the UI
- add custom JavaScript to the UI

Plugin tasks can be implemented using embedded Javascript, or by calling an external binary.

> **⚠️ Note:** Plugin support is still experimental and is likely to change.

## Managing Plugins

Plugins can be installed and managed from the `Settings > Plugins` page. 

Plugins are installed using the `Available Plugins` section. This section allows configuring sources from which to install plugins. The `Community (stable)` source is configured by default. This source contains plugins for the current _stable_ version of stash.

These are the plugin sources maintained by the stashapp organisation:

| Name | Source URL | Recommended Local Path | Notes |
|------|-----------|------------------------|-------|
| Community (stable) | `https://stashapp.github.io/CommunityScripts/stable/index.yml` | `stable` | For the current stable version of stash. |
| Community (develop) | `https://stashapp.github.io/CommunityScripts/develop/index.yml` | `develop` | For the develop version of stash. |

Installed plugins can be updated or uninstalled from the `Installed Plugins` section.

### Source URLs

The source URL must return a yaml file containing all the available packages for the source. An example source yaml file looks like the following:

```
- id: <package id>
  name: <package name>
  version: <version>
  date: <date>
  requires:
  - <ids of packages required by this package (optional)>
  - ...
  path: <path to package zip file>
  sha256: <sha256 of zip>
  metadata:
    <optional key/value pairs for extra information>
- ...
```

Path can be a relative path to the zip file or an external URL.

## Adding plugins manually

By default, Stash looks for plugin configurations in the `plugins` sub-directory of the directory where the stash `config.yml` is read. This will either be the `$HOME/.stash` directory or the current working directory.

Plugins are added by adding configuration yaml files (format: `pluginName.yml`) to the `plugins` directory.

Loaded plugins can be viewed in the Plugins page of the Settings. After plugins are added, removed or edited while stash is running, they can be reloaded by clicking `Reload Plugins` button.

## Using plugins

Plugins provide tasks which can be run from the Tasks page. 

## Creating plugins

### Plugin configuration file format

The basic structure of a plugin configuration file is as follows:

```yaml
name: <plugin name> 
# optional list of dependencies to be included
# "#" is is part of the config - do not remove
# requires: <plugin ID>
description: <optional description of the plugin>
version: <optional version tag>
url: <optional url>

ui:
  # optional list of css files to include in the UI
  css:
    - <path to css file>

  # optional list of js files to include in the UI
  javascript:
    - <path to javascript file>

  # optional list of plugin IDs to load prior to this plugin
  requires:
    - <plugin ID>

  # optional list of assets 
  assets:
    urlPrefix: fsLocation
    ...

  # content-security policy overrides
  csp:
    script-src:
      - http://alloweddomain.com
    
    style-src:
      - http://alloweddomain.com
    
    connect-src:
      - http://alloweddomain.com

# map of setting names to be displayed in the plugins page in the UI
settings:
  # internal name
  foo:
  # name to display in the UI
  displayName: Foo
  # type of the attribute to show in the UI
  # can be BOOLEAN, NUMBER, or STRING
  type: BOOLEAN

# the following are used for plugin tasks only
exec:
  - ...
interface: [interface type]
errLog: [one of none trace, debug, info, warning, error]
tasks:
  - ...
```

The `name`, `description`, `version` and `url` fields are displayed on the plugins page.

`# requires` will make the plugin manager select plugins matching the specified IDs to be automatically installed as dependencies. Only works with plugins within the same index.

The `exec`, `interface`, `errLog` and `tasks` fields are used only for plugins with tasks.

The `settings` field is used to display plugin settings on the plugins page. Plugin settings can also be set using the graphql mutation `configurePlugin` - the settings set this way do _not_ need to be specified in the `settings` field unless they are to be displayed in the stock plugin settings UI.

### UI Configuration

The `css` and `javascript` field values may be relative paths to the plugin configuration file, or
may be full external URLs.

The `requires` field is a list of plugin IDs which must have their javascript/css files loaded
before this plugins javascript/css files.

The `assets` field is a map of URL prefixes to filesystem paths relative to the plugin configuration file.
Assets are mounted to the `/plugin/{pluginID}/assets` path. 

As an example, for a plugin with id `foo` with the following `assets` value:
```
assets:
  foo: bar
  /: .
```
The following URLs will be mapped to these locations:
`/plugin/foo/assets/foo/file.txt` -> `{pluginDir}/bar/file.txt`
`/plugin/foo/assets/file.txt` -> `{pluginDir}/file.txt`
`/plugin/foo/assets/bar/file.txt` -> `{pluginDir}/bar/file.txt` (via the `/` entry)

Mappings that try to go outside of the directory containing the plugin configuration file will be
ignored.

The `csp` field contains overrides to the content security policies. The URLs in `script-src`,
`style-src` and `connect-src` will be added to the applicable content security policy.

See [External Plugins](/help/ExternalPlugins.md) for details for making plugins with external tasks.

See [Embedded Plugins](/help/EmbeddedPlugins.md) for details for making plugins with embedded tasks.

### Plugin task input

Plugin tasks may accept an input from the stash server. This input is encoded according to the interface, and has the following structure (presented here in JSON format):
```
{
    "server_connection": {
        "Scheme": "http",
        "Port": 9999,
        "SessionCookie": {
            "Name":"session",
            "Value":"cookie-value",
            "Path":"",
            "Domain":"",
            "Expires":"0001-01-01T00:00:00Z",
            "RawExpires":"",
            "MaxAge":0,
            "Secure":false,
            "HttpOnly":false,
            "SameSite":0,
            "Raw":"",
            "Unparsed":null
        },
        "Dir": <path to stash config directory>,
        "PluginDir": <path to plugin config directory>,
    },
    "args": {
        "argKey": "argValue"
    }
}
```

The `server_connection` field contains all the information needed for a plugin to access the parent stash server, if necessary.

### Plugin task output

Plugin task output is expected in the following structure (presented here as JSON format):

```
{
    "error": <optional error string>
    "output": <anything>
}
```

The `error` field is logged in stash at the `error` log level if present. The `output` is written at the `debug` log level.

### Task configuration

Tasks are configured using the following structure:

```
tasks:
  - name: <operation name>
    description: <optional description>
    defaultArgs:
      argKey: argValue
```

A plugin configuration may contain multiple tasks. 

The `defaultArgs` field is used to add inputs to the plugin input sent to the plugin.

### Hook configuration

Stash supports executing plugin operations via triggering of a hook during a stash operation.

Hooks are configured using a similar structure to tasks:

```
hooks:
  - name: <operation name>
    description: <optional description>
    triggeredBy:
      - <trigger types>...
    defaultArgs:
      argKey: argValue
```

**⚠️ Note:** It is possible for hooks to trigger eachother or themselves if they perform mutations. For safety, hooks will not be triggered if they have already been triggered in the context of the operation. Stash uses cookies to track this context, so it's important for plugins to send cookies when performing operations.

#### Trigger types

Trigger types use the following format: `<object type>.<operation>.<hook type>`

For example, a post-hook on a scene create operation will be `Scene.Create.Post`.

The following object types are supported:

* `Scene`
* `SceneMarker`
* `Image`
* `Gallery`
* `Group`
* `Performer`
* `Studio`
* `Tag`

The following operations are supported:

* `Create`
* `Update`
* `Destroy`
* `Merge` (for `Tag` only)

Currently, only `Post` hook types are supported. These are executed after the operation has completed and the transaction is committed.

#### Hook input

Plugin tasks triggered by a hook include an argument named `hookContext` in the `args` object structure. The `hookContext` is structured as follows:

```
{
    "id": <object id>,
    "type": <trigger type>,
    "input": <operation input>,
    "inputFields": <fields included in input>
}
```

The `input` field contains the JSON graphql input passed to the original operation. This will differ between operations. For hooks triggered by operations in a scan or clean, the input will be nil. `inputFields` is populated in update operations to indicate which fields were passed to the operation, to differentiate between missing and empty fields.

For example, here is the `args` values for a Scene update operation:

```
{
    "hookContext": {
        "type":"Scene.Update.Post",
        "id":45,
        "input":{
            "clientMutationId":null,
            "id":"45",
            "title":null,
            "details":null,
            "url":null,
            "date":null,
            "rating":null,
            "organized":null,
            "studio_id":null,
            "gallery_ids":null,
            "performer_ids":null,
            "groups":null,
            "tag_ids":["21"],
            "cover_image":null,
            "stash_ids":null
        },
        "inputFields":[
            "tag_ids",
            "id"
        ]
    }
}
```
# External Plugin Tasks

External plugin tasks are executed by running an external binary.

## Plugin interfaces

Stash communicates with external plugin tasks using an interface. Stash currently supports RPC and raw interface types.

### RPC interface

The RPC interface uses JSON-RPC to communicate with the plugin process. A golang plugin utilising the RPC interface is available in the stash source code under `pkg/plugin/examples/gorpc`. RPC plugins are expected to provide an interface that fulfils the `RPCRunner` interface in `pkg/plugin/common`.

RPC plugins are expected to accept requests asynchronously.

When stopping an RPC plugin task, the stash server sends a stop request to the plugin and relies on the plugin to stop itself.

### Raw interface

Raw interface plugins are not required to conform to any particular interface. The stash server will send the plugin input to the plugin process via its stdin stream, encoded as JSON. Raw interface plugins are not required to read the input.

The stash server reads stdout for the plugin's output. If the output can be decoded as a JSON representation of the plugin output data structure then it will do so. If not, it will treat the entire stdout string as the plugin's output.

When stopping a raw plugin task, the stash server kills the spawned process without warning or signals.

## Logging

External plugins may log to the stash server by writing to stderr. By default, data written to stderr will be logged by stash at the `error` level. This default behaviour can be changed by setting the `errLog` field in the plugin configuration file.

Plugins can log for specific levels or log progress by prefixing the output string with special control characters. See `pkg/plugin/common/log` for how this is done in go.

## Plugin configuration file format

### exec

For external plugin tasks, the `exec` field is a list with the first element being the binary that will be executed, and the subsequent elements are the arguments passed. The execution process will search the path for the binary, then will attempt to find the program in the same directory as the plugin configuration file. The `exe` extension is not necessary on Windows systems. 

> **⚠️ Note:** The plugin execution process sets the current working directory to that of the stash process.

Arguments can include the plugin's directory with the special string `{pluginDir}`. 

For example, if the plugin executable `my_plugin` is placed in the `plugins` subdirectory and requires arguments `foo` and `bar`, then the `exec` part of the configuration would look like the following:

```
exec:
  - my_plugin
  - foo
  - bar
```

Another example might use a python script to execute the plugin. Assuming the python script `foo.py` is placed in the same directory as the plugin config file, the `exec` fragment would look like the following:

```
exec:
  - python
  - {pluginDir}/foo.py
```

### interface

For external plugin tasks, the `interface` field must be set to one of the following values:
* `rpc`
* `raw`

See the `Plugin interfaces` section above for details on these interface types.

The `interface` field defaults to `raw` if not provided.

### errLog

The `errLog` field tells stash what the default log level should be when the plugin outputs to stderr without encoding a log level. It defaults to the `error` level if no provided. This field is not necessary if the plugin outputs logging with the appropriate encoding. See the `Logging` section above for details.

## Task configuration

In addition to the standard task configuration, external tasks may be configured with an optional `execArgs` field to add extra parameters to the execution arguments for the task.

For example:

```
tasks:
  - name: <operation name>
    description: <optional description>
    execArgs:
      - <arg to add to the exec line>
```

# Embedded Plugin Tasks

Embedded plugin tasks are executed within the stash process using a scripting system.

## Supported script languages

Stash currently supports Javascript embedded plugin tasks using [goja](https://github.com/dop251/goja).

## Javascript plugins

### Plugin input

The input is provided to Javascript plugin tasks using the `input` global variable, and is an object based on the structure provided in the `Plugin input` section of the [Plugins](/help/Plugins.md) page. 

> **⚠️ Note:** `server_connection` field should not be necessary in most embedded plugins.

### Plugin output

The output of a Javascript plugin task is derived from the evaluated value of the script. The output should conform to the structure provided in the `Plugin output` section of the [Plugins](/help/Plugins.md) page.

There are a number of ways to return the plugin output:

#### Example #1
```
(function() {
    return {
        Output: "ok"
    };
})();
```

#### Example #2
```
function main() {
    return {
        Output: "ok"
    };
}

main();
```

#### Example #3
```
var output = {
    Output: "ok"
};

output;
```

## Logging

See the `Javascript API` section below on how to log with Javascript plugins.

## Plugin configuration file format

### exec

For embedded plugins, the `exec` field is a list with the first element being the path to the Javascript file that will be executed. It is expected that the path to the Javascript file is relative to the directory of the plugin configuration file.

### interface

For embedded plugins, the `interface` field must be set to one of the following values:
* `js`

## Javascript API

### Logging

Stash provides the following API for logging in Javascript plugins:

| Method | Description |
|--------|-------------|
| `log.Trace(<string>)` | Log with the `trace` log level. |
| `log.Debug(<string>)` | Log with the `debug` log level. |
| `log.Info(<string>)` | Log with the `info` log level. |
| `log.Warn(<string>)` | Log with the `warn` log level. |
| `log.Error(<string>)` | Log with the `error` log level. |
| `log.Progress(<float between 0 and 1>)` | Sets the progress of the plugin task, as a float, where `0` represents 0% and `1` represents 100%. |

### GQL

Stash provides the following API for communicating with stash using the graphql interface:

| Method | Description |
|--------|-------------|
| `gql.Do(<query/mutation string>, <variables object>)` | Executes a graphql query/mutation on the stash server. Returns an object in the same way as a graphql query does. |

#### Example

```
// creates a tag
var mutation = "\
mutation tagCreate($input: TagCreateInput!) {\
  tagCreate(input: $input) {\
    id\
  }\
}";

var variables = {
    input: {
        'name': tagName
    }
};

result = gql.Do(mutation, variables);
log.Info("tag id = " + result.tagCreate.id);
```

## Utility functions

Stash provides the following API for utility functions:

| Method | Description |
|--------|-------------|
| `util.Sleep(<milliseconds>)` | Suspends the current thread for the specified duration. |


# UI Plugin API

The `PluginApi` object is a global object in the `window` object.

`PluginApi` is considered experimental and is subject to change without notice. This documentation covers only the plugin-specific API. It does not necessarily cover the core UI API. Information on these methods should be referenced in the UI source code.

An example using various aspects of `PluginApi` may be found in the source code under `pkg/plugin/examples/react-component`.

## Properties

### `React`

An instance of the React library.

### `ReactDOM`

An instance of the ReactDOM library.

### `GQL`

This namespace contains the generated graphql client interface. This is a low-level interface. In many cases, `StashService` should be used instead.

### `libraries`

`libraries` provides access to the following UI libraries:

- `ReactRouterDOM`
- `Bootstrap`
- `Apollo`
- `Intl`
- `FontAwesomeRegular`
- `FontAwesomeSolid`
- `FontAwesomeBrands`
- `Mousetrap`
- `MousetrapPause`
- `ReactFontAwesome`
- `ReactSelect`

### `register`

This namespace contains methods used to register page routes and components.

#### `PluginApi.register.route`

Registers a route in the React Router.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `string` | The path to register. This should generally use the `/plugin/` prefix. |
| `component` | `React.FC` | A React function component that will be rendered when the route is loaded. |

Returns `void`.

#### `PluginApi.register.component`

Registers a component to be used by plugins. The component will be available in the `components` namespace.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `string` | The name of the component to register. This should be unique and should ideally be prefixed with `plugin-`. |
| `component` | `React.FC` | A React function component. |

Returns `void`.

### `components`

This namespace contains all of the components available to plugins. These include a selection of core components and components registered using `PluginApi.register.component`.

### `utils`

This namespace provides access to the `NavUtils` , `StashService` and `InteractiveUtils` namespaces. It also provides access to the `loadComponents` method.

#### `PluginApi.utils.loadComponents`

Due to code splitting, some components may not be loaded and available when a plugin page is rendered. `loadComponents` loads all of the components that a plugin page may require.

In general, `PluginApi.hooks.useLoadComponents` hook should be used instead.

| Parameter | Type | Description |
|-----------|------|-------------|
| `components` | `Promise[]` | The list of components to load. These values should come from the `PluginApi.loadableComponents` namespace. |

Returns a `Promise<void>` that resolves when all of the components have been loaded.

#### `PluginApi.utils.InteractiveUtils`
This namespace provides access to `interactiveClientProvider` and `getPlayer`
 - `getPlayer` returns the current `videojs` player object
 - `interactiveClientProvider` takes `IInteractiveClientProvider` which allows a developer to hook into the lifecycle of funscripts.
```ts
  export interface IDeviceSettings {
  connectionKey: string;
  scriptOffset: number;
  estimatedServerTimeOffset?: number;
  useStashHostedFunscript?: boolean;
  [key: string]: unknown;
}

export interface IInteractiveClientProviderOptions {
  handyKey: string;
  scriptOffset: number;
  defaultClientProvider?: IInteractiveClientProvider;
  stashConfig?: GQL.ConfigDataFragment;
}
export interface IInteractiveClientProvider {
  (options: IInteractiveClientProviderOptions): IInteractiveClient;
}

/**
 * Interface that is used for InteractiveProvider
 */
export interface IInteractiveClient {
  connect(): Promise<void>;
  handyKey: string;
  uploadScript: (funscriptPath: string, apiKey?: string) => Promise<void>;
  sync(): Promise<number>;
  configure(config: Partial<IDeviceSettings>): Promise<void>;
  play(position: number): Promise<void>;
  pause(): Promise<void>;
  ensurePlaying(position: number): Promise<void>;
  setLooping(looping: boolean): Promise<void>;
  readonly connected: boolean;
  readonly playing: boolean;
}

```
##### Example
For instance say I wanted to add extra logging when `IInteractiveClient.connect()` is called.
In my plugin you would install your own client provider as seen below

```ts
InteractiveUtils.interactiveClientProvider = (
  opts
) => {
  if (!opts.defaultClientProvider) {
    throw new Error('invalid setup');
  }

  const client = opts.defaultClientProvider(opts);
  const connect = client.connect;
  client.connect = async () => {
      console.log('patching connect method');
      return connect.call(client);
    };
   
  return client;
};

```


### `hooks`

This namespace provides access to the following core utility hooks:

- `useGalleryLightbox`
- `useLightbox`
- `useSpriteInfo`
- `useToast`

It also provides plugin-specific hooks.

#### `PluginApi.hooks.useLoadComponents`

This is a hook used to load components, using the `PluginApi.utils.loadComponents` method.

| Parameter | Type | Description |
|-----------|------|-------------|
| `components` | `Promise[]` | The list of components to load. These values should come from the `PluginApi.loadableComponents` namespace. |

Returns a `boolean` which will be `true` if the components are loading.

### `loadableComponents`

This namespace contains all of the components that may need to be loaded using the `loadComponents` method. Components are added to this namespace as needed. Please make a development request if a required component is not in this namespace.

This component also includes coarse-grained entries for every lazily loaded import in the stock UI. If a component is not available in `components` when the page loads, it can be loaded using the coarse-grained entry. For example, `PerformerCard` can be loaded using `loadableComponents.Performers`.

### `patch`

This namespace provides methods to patch components to change their behaviour.

#### `PluginApi.patch.before`

Registers a before function. A before function is called prior to calling a component's render function. It accepts the same parameters as the component's render function, and is expected to return a list of new arguments that will be passed to the render.

| Parameter | Type | Description |
|-----------|------|-------------|
| `component` | `string` | The name of the component to patch. |
| `fn` | `Function` | The before function. It accepts the same arguments as the component render function and is expected to return a list of arguments to pass to the render function. |

Returns `void`.

#### `PluginApi.patch.instead`

Registers a replacement function for a component. The provided function will be called with the arguments passed to the original render function, plus the next render function as the last argument. Replacement functions will be called in the order that they are registered. If a replacement function does not call the next render function then the following replacement functions will not be called or applied.

| Parameter | Type | Description |
|-----------|------|-------------|
| `component` | `string` | The name of the component to patch. |
| `fn` | `Function` | The replacement function. It accepts the same arguments as the original render function, plus the next render function, and is expected to return the replacement component. |

Returns `void`.

#### `PluginApi.patch.after`

Registers an after function. An after function is called after the render function of the component. It accepts the arguments passed to the original render function, plus the result of the original render function. It is expected to return the rendered component.

| Parameter | Type | Description |
|-----------|------|-------------|
| `component` | `string` | The name of the component to patch. |
| `fn` | `Function` | The after function. It accepts the same arguments as the original render function, plus the result of the original render function, and is expected to return the rendered component. |

Returns `void`.

#### Patchable components and functions

- `AlertModal`
- `App`
- `BackgroundImage`
- `BooleanSetting`
- `ChangeButtonSetting`
- `CompressedPerformerDetailsPanel`
- `ConstantSetting`
- `CountrySelect`
- `CustomFieldInput`
- `CustomFields`
- `CustomFieldsInput`
- `DateInput`
- `DetailImage`
- `ExternalLinkButtons`
- `ExternalLinksButton`
- `FilteredGalleryList`
- `FilteredGroupList`
- `FilteredImageList`
- `FilteredPerformerList`
- `FilteredSceneList`
- `FilteredSceneMarkerList`
- `FilteredStudioList`
- `FilteredTagList`
- `FolderSelect`
- `FrontPage`
- `GalleryCard`
- `GalleryCard.Details`
- `GalleryCard.Image`
- `GalleryCard.Overlays`
- `GalleryCard.Popovers`
- `GalleryCardGrid`
- `GalleryIDSelect`
- `GalleryList`
- `GalleryRecommendationRow`
- `GallerySelect`
- `GallerySelect.sort`
- `GridCard`
- `GroupCard`
- `GroupCardGrid`
- `GroupIDSelect`
- `GroupList`
- `GroupRecommendationRow`
- `GroupSelect`
- `GroupSelect.sort`
- `HeaderImage`
- `HoverPopover`
- `Icon`
- `ImageCard`
- `ImageCard.Details`
- `ImageCard.Image`
- `ImageCard.Overlays`
- `ImageCard.Popovers`
- `ImageDetailPanel`
- `ImageGridCard`
- `ImageInput`
- `ImageList`
- `ImageRecommendationRow`
- `LightboxLink`
- `LoadingIndicator`
- `MainNavBar.MenuItems`
- `MainNavBar.UtilityItems`
- `ModalSetting`
- `NumberSetting`
- `Pagination`
- `PaginationIndex`
- `PerformerAppearsWithPanel`
- `PerformerCard`
- `PerformerCard.Details`
- `PerformerCard.Image`
- `PerformerCard.Overlays`
- `PerformerCard.Popovers`
- `PerformerCard.Title`
- `PerformerCardGrid`
- `PerformerDetailsPanel`
- `PerformerDetailsPanel.DetailGroup`
- `PerformerGalleriesPanel`
- `PerformerGroupsPanel`
- `PerformerHeaderImage`
- `PerformerIDSelect`
- `PerformerImagesPanel`
- `PerformerList`
- `PerformerPage`
- `PerformerRecommendationRow`
- `PerformerScenesPanel`
- `PerformerSelect`
- `PerformerSelect.sort`
- `PluginRoutes`
- `PluginSettings`
- `RatingNumber`
- `RatingStars`
- `RatingSystem`
- `RecommendationRow`
- `SceneCard`
- `SceneCard.Details`
- `SceneCard.Image`
- `SceneCard.Overlays`
- `SceneCard.Popovers`
- `SceneCard.SceneSpecs`
- `SceneCardsGrid`
- `SceneFileInfoPanel`
- `SceneIDSelect`
- `SceneMarkerCard`
- `SceneMarkerCard.Details`
- `SceneMarkerCard.Image`
- `SceneMarkerCard.Popovers`
- `SceneMarkerCardsGrid`
- `SceneMarkerList`
- `SceneMarkerRecommendationRow`
- `SceneList`
- `ScenePage`
- `ScenePage.TabContent`
- `ScenePage.Tabs`
- `ScenePlayer`
- `SceneRecommendationRow`
- `SceneSelect`
- `SceneSelect.sort`
- `SelectSetting`
- `Setting`
- `SettingGroup`
- `SettingModal`
- `StringListSetting`
- `StringSetting`
- `StudioCard`
- `StudioCardGrid`
- `StudioDetailsPanel`
- `StudioIDSelect`
- `StudioList`
- `StudioRecommendationRow`
- `StudioSelect`
- `StudioSelect.sort`
- `SweatDrops`
- `TabTitleCounter`
- `TagCard`
- `TagCard.Details`
- `TagCard.Image`
- `TagCard.Overlays`
- `TagCard.Popovers`
- `TagCard.Title`
- `TagCardGrid`
- `TagIDSelect`
- `TagLink`
- `TagList`
- `TagRecommendationRow`
- `TagSelect`
- `TagSelect.sort`
- `TruncatedText`

### `PluginApi.Event`

Allows plugins to listen for Stash's events.

```js
PluginApi.Event.addEventListener("stash:location", (e) => console.log("Page Changed", e.detail.data.location.pathname))
```

Large Collection of Example Plugins

https://github.com/stashapp/CommunityScripts/tree/main/plugins