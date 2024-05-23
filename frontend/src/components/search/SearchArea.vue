<script setup>
import { mapStores } from "pinia"
import {
  AdjustmentsHorizontalIcon,
  MinusCircleIcon,
  HomeIcon,
  ClockIcon,
  BookmarkIcon,
  MagnifyingGlassIcon,
  ChatBubbleLeftIcon,
  PaperAirplaneIcon,
} from "@heroicons/vue/24/outline"
import MultiSelect from 'primevue/multiselect';
import Chip from 'primevue/chip';
import OverlayPanel from 'primevue/overlaypanel';
import InputSwitch from 'primevue/inputswitch';
import ProgressSpinner from 'primevue/progressspinner';

import { httpClient, djangoClient } from "../../api/httpClient"
import { FieldType, ellipse } from "../../utils/utils"
import { useAppStateStore } from "../../stores/app_state_store"
import CollectionAndVectorFieldSelection from "./CollectionAndVectorFieldSelection.vue";
import LoginButton from "../LoginButton.vue";
import AddFilterMenu from "./AddFilterMenu.vue";
import SearchFilterList from "./SearchFilterList.vue";
import UserMenu from "./UserMenu.vue";
import SearchHistoryDialog from "../history/SearchHistoryDialog.vue";
import StoredMapsDialog from "../history/StoredMapsDialog.vue";
import { useToast } from 'primevue/usetoast';
const toast = useToast()

const appState = useAppStateStore()
const _window = window
const _history = history
</script>

<script>
// combined: all fields in "default search fields" with same query (+negatives), as OR, reciprocal rank fusion

// fulltext: opensearch, all text fields, opensearch dql language for negatives
//    - "must": add to AND set
// description_vector: vector search, knee threshold function, minus operator for negatives
//    - generator -> embedding space -> other generators -> set of types -> fields
//    - "more / less results slider": change knee algo setting
//    - "must": add to AND set
// image_vector: vector search, knee threshold function, minus operator for negatives
//    - "more / less results slider": change knee algo setting
//    - "must": add to AND set
// filter out items that are not in AND sets, reciprocal rank fusion

// auto generated filter criteria set (later, maybe simple ones for now)

// external input: combined (pos, neg, text),
//     separate fields (pos, neg with text or image (if supported)),
// similar to item (list of fields, e.g. descr. or image, fields are OR),
// matching to classifier (classifier id),
// cluster id of map id

export default {
  inject: ["eventBus"],
  emits: ["request_search_results", "reset_search_box"],
  data() {
    return {
      internal_organization_id: null,

      smart_query: "",
      use_smart_search: false,
      processing_smart_search: false,
      show_negative_query_field: false,
      show_settings: false,

      show_search_settings: false,
      show_autocut_settings: false,
      show_vectorize_settings: false,
      show_projection_settings: false,
      show_rendering_settings: false,
      show_frontend_settings: false,
      show_other_settings: false,

      available_autocut_strategies: [
        { id: "static_threshold", title: "Static Threshold" },
        { id: "knee_point", title: "Knee Point" },
        { id: "nearest_neighbour_distance_ration", title: "Neighbour Distance" },
      ],
      available_tokenizer: [
        { id: "default", title: "default" },
        { id: "absclust", title: "AbsClust Tokenizer" },
        { id: "simple", title: "simple" },
      ],
      available_dim_reducers: [
        { id: "umap", title: "UMAP" },
        { id: "umap_cuml_gpu", title: "UMAP (GPU)" },
        { id: "pacmap", title: "PaCMAP" },
      ],
      axis_type_options: [
        { id: "embedding", title: "Embedding" },
        { id: "number_field", title: "Number Field" },
        { id: "count", title: "Array / Word Count" },
        { id: "classifier", title: "Classifier" },
        { id: "rank", title: "Rank" },
        { id: "score", title: "Score" },
        { id: "keyword_score", title: "Score (Keyword)" },
      ],
      rendering_type_options: [
        { id: "fixed", title: "Fixed" },
        { id: "embedding", title: "Embedding" },
        { id: "umap_perplexity", title: "UMAP Perplexity" },
        { id: "number_field", title: "Number Field" },
        { id: "count", title: "Array / Word Count" },
        { id: "classifier", title: "Classifier" },
        { id: "rank", title: "Rank" },
        { id: "score", title: "Score" },
        { id: "keyword_score", title: "Score (Keyword)" },
        { id: "cluster_idx", title: "Cluster Id" },
        { id: "origin_query_idx", title: "Origin Query" },
        { id: "contains", title: "Contains" },
        { id: "is_empty", title: "Is empty" },
      ],
      available_clusterizer: [{ id: "hdbscan", title: "HDBSCAN" }],
      available_cluster_title_strategies: [
        { id: "tf_idf_top_3", title: "tf_idf_top_3" },
        { id: "generative_ai", title: "generative_ai" },
      ],
      rendering_parameters: [
        ["size", "Size"],
        ["hue", "Hue"],
        ["sat", "Saturation"],
        ["val", "Value"],
        ["opacity", "Opacity"],
        ["secondary_hue", "2nd Hue"],
        ["secondary_sat", "2nd Sat"],
        ["secondary_val", "2nd Val"],
        ["secondary_opacity", "2nd Opa."],
        ["flatness", "Flatness"],
      ],
      available_styles: [
        { id: "3d", title: "3D" },
        { id: "plotly", title: "Plotly" },
      ],
    }
  },
  mounted() {
    const that = this
    this.internal_organization_id = this.appStateStore.organization_id
    this.eventBus.on("show_results_tab", () => {
      that.use_smart_search = false
    })
  },
  computed: {
    ...mapStores(useAppStateStore),
    query_uses_operators_and_meaning() {
      const uses_meaning = ["vector", "hybrid"].includes(this.appStateStore.settings.search.search_algorithm)
      const operators = [" AND ", " OR ", " NOT "]
      const uses_operators = operators.some((op) => this.appStateStore.settings.search.all_field_query.includes(op))
      return uses_operators && uses_meaning
    },
    query_includes_other_quotes() {
      const other_quotes = ["'", "`", "´", "‘", "’", "“", "”", "„", "‟", "❛", "❜", "❝", "❞", "＇", "＂"]
      const query = this.appStateStore.settings.search.all_field_query
      return other_quotes.some((quote) => query.includes(" " + quote) || query.includes(quote + " "))
    },
  },
  watch: {
    "appStateStore.organization_id": function (newValue, oldValue) {
      // using internal variable to be able to reset parameters before
      // actually changing global dataset_id in select-field listener below
      this.internal_organization_id = this.appStateStore.organization_id
    },
    show_negative_query_field() {
      if (!this.show_negative_query_field) {
        this.appStateStore.settings.search.all_field_query_negative = ""
      }
    },
  },
  methods: {
    organization_id_changed_by_user() {
      this.appStateStore.set_organization_id(this.internal_organization_id)
    },
    open_search_history_dialog() {
      this.$dialog.open(SearchHistoryDialog, {props: {header: "Search History", modal: true}});
    },
    open_stored_maps_dialog() {
      this.$dialog.open(StoredMapsDialog, {props: {header: "Stored Maps", modal: true}});
    },
    run_smart_search() {
      if (this.processing_smart_search) return
      djangoClient.post(`/org/data_map/convert_smart_query_to_parameters`, {
        user_id: this.appStateStore.user.id,
        query: this.smart_query,
      }).then((response) => {
        this.processing_smart_search = false
        const search_parameters = response.data.search_parameters
        this.appStateStore.settings.search.all_field_query = search_parameters.query
        for (const filter of search_parameters.filters) {
          filter.dataset_id = this.appStateStore.settings.search.dataset_ids[0]
        }
        this.appStateStore.settings.search.filters = search_parameters.filters || []
        if (search_parameters.search_type == "meaning") {
          search_parameters.search_type = "vector"
        }
        this.appStateStore.settings.search.search_algorithm = search_parameters.search_type
        this.use_smart_search = false
        this.appStateStore.request_search_results()
      }).catch((error) => {
        console.log(error)
        this.processing_smart_search = false
        this.$toast.add({severity: 'error', summary: 'Error', detail: 'Smart search failed', life: 5000})
      })
      this.processing_smart_search = true
    },
  },
}
</script>

<template>
  <div class="px-3 pt-3 pb-2 pointer-events-auto rounded-md bg-white shadow-sm">
    <!-- Database Selection -->
    <div class="mb-2 flex items-center justify-between">
      <a
        v-tooltip.right="{ value: 'Reset search', showDelay: 400 }"
        :href="`?organization_id=${appState.organization_id}`"
        class="w-8 rounded p-2 text-gray-500 hover:bg-gray-100">
        <HomeIcon></HomeIcon>
      </a>

      <div class="ml-1 flex-initial w-28"
        v-tooltip.bottom="{ value: 'Select the organization', showDelay: 400 }">
        <select
          v-model="internal_organization_id"
          @change="organization_id_changed_by_user"
          class="w-full rounded-md border-transparent pb-1 pl-2 pr-8 pt-1 text-sm font-['Lexend'] font-bold text-black focus:border-blue-500 focus:ring-blue-500">
          <option v-for="item in appState.available_organizations" :value="item.id" selected>
            {{ item.name }}
          </option>
        </select>
      </div>

      <div class="flex-initial w-48"
        v-tooltip.bottom="{ value: 'Datasets to search in', showDelay: 400 }">
        <MultiSelect v-model="appState.settings.search.dataset_ids"
          :options="Object.values(appState.datasets)"
          optionLabel="name"
          optionValue="id"
          placeholder="Select Source..."
          @change="appState.on_selected_datasets_changed"
          class="w-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
      </div>
      <!-- <button
        @click="appState.show_global_map()"
        title="Show all items (or a representative subset if there are too many)"
        class="ml-1 rounded-md px-2 h-7 text-sm text-gray-500 bg-gray-100 hover:bg-blue-100/50">
        Overview
      </button> -->

      <div class="flex-1"></div>
      <div class="flex flex-row items-center" v-tooltip="{value: 'Auto-detect best search type and required filters from a natural language query', showDelay: 400}">
        <InputSwitch v-model="use_smart_search" class="" />
        <span class="ml-2 text-sm text-gray-500">
          Smart
        </span>
      </div>

      <div class="flex-1"></div>
      <LoginButton></LoginButton>
      <button v-if="appState.logged_in" class="mr-2 p-1 text-sm text-gray-500 rounded-md hover:bg-gray-100"
        v-tooltip.bottom="{ value: 'User Menu (logout etc.)', showDelay: 400 }"
        @click="(event) => $refs.user_menu.toggle(event)">
        <!-- <UserCircleIcon class="inline-block w-4 h-4"></UserCircleIcon> -->
        {{ appState.user.username.substring(0, 6) + (appState.user.username.length > 6 ? '...' : '') }}
      </button>

      <OverlayPanel ref="user_menu">
        <UserMenu @hide="$refs.user_menu.hide()"></UserMenu>
      </OverlayPanel>
    </div>

    <!-- Search Field -->
    <div v-if="use_smart_search && appState.settings.search.search_type == 'external_input'" class="flex flex-row items-center">
      <div class="flex h-9 flex-1 flex-row items-center">
        <input
          type="search"
          name="search"
          @keyup.enter="run_smart_search()"
          v-model="smart_query"
          :placeholder="`Describe what ${appState.settings.search.dataset_ids.length ? appState.datasets[appState.settings.search.dataset_ids[0]]?.entity_name || '' : ''} you want to find`"
          class="h-full w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
      </div>
      <button v-if="!processing_smart_search"
        v-tooltip.bottom="{value: 'Submit (auto search or chat)', showDelay: 400}"
        class="ml-2 px-2 h-9 rounded-md shadow-sm border-gray-300 border bg-gray-100 hover:bg-blue-100/50 text-sm text-gray-500"
        @click="run_smart_search()">
        <PaperAirplaneIcon class="h-5 w-5"></PaperAirplaneIcon>
      </button>
      <ProgressSpinner v-if="processing_smart_search" class="ml-1 w-5 h-5"></ProgressSpinner>
    </div>
    <div v-if="!use_smart_search" class="flex flex-row items-center">
      <div
        v-if="appState.settings.search.search_type != 'external_input'"
        class="flex h-9 flex-1 flex-row items-center">
        <Chip v-if="appState.settings.search.search_type == 'cluster'"
          class="text-sm font-semibold">
          Cluster '{{ ellipse(appState.settings.search.origin_display_name, 15) }}'
          <!-- don't use built-in 'removable' feature of Chip because it would remove the element even for page before -->
          <button @click="_history.back()" v-tooltip="{value: 'Go to previous view', showDelay: 400}"
            class="ml-1 h-4 w-4 flex items-center justify-center rounded-full bg-white text-xs text-gray-500">X</button>
        </Chip>
        <Chip v-if="appState.settings.search.search_type == 'map_subset'"
          class="text-sm font-semibold">
          Custom Selection
          <!-- don't use built-in 'removable' feature of Chip because it would remove the element even for page before -->
          <button @click="_history.back()" v-tooltip="{value: 'Go to previous view', showDelay: 400}"
            class="ml-1 h-4 w-4 flex items-center justify-center rounded-full bg-white text-xs text-gray-500">X</button>
        </Chip>
        <Chip v-if="appState.settings.search.search_type == 'similar_to_item'"
          class="text-sm font-semibold">
          Similar to item '{{ ellipse(appState.settings.search.origin_display_name, 15) }}'
          <!-- don't use built-in 'removable' feature of Chip because it would remove the element even for page before -->
          <button @click="_history.back()" v-tooltip="{value: 'Go to previous view', showDelay: 400}"
            class="ml-1 h-4 w-4 flex items-center justify-center rounded-full bg-white text-xs text-gray-500">X</button>
        </Chip>
        <Chip v-if="appState.settings.search.search_type == 'collection'"
          class="text-sm font-semibold">
          Collection '{{ ellipse(appState.settings.search.origin_display_name, 15) }}'
          <!-- don't use built-in 'removable' feature of Chip because it would remove the element even for page before -->
          <button @click="appState.reset_search_box(); appState.reset_search_results_and_map()"
            class="ml-1 h-4 w-4 flex items-center justify-center rounded-full bg-white text-xs text-gray-500">X</button>
        </Chip>
        <Chip v-if="appState.settings.search.search_type == 'recommended_for_collection'"
          class="text-sm font-semibold">
          Recommended for Collection '{{
            ellipse(appState.settings.search.origin_display_name, 15)
          }}'
          <!-- don't use built-in 'removable' feature of Chip because it would remove the element even for page before -->
          <button @click="appState.reset_search_box(); appState.reset_search_results_and_map()"
            class="ml-1 h-4 w-4 flex items-center justify-center rounded-full bg-white text-xs text-gray-500">X</button>
        </Chip>
        <Chip v-if="appState.settings.search.search_type == 'global_map'"
          class="text-sm font-semibold">
          Overview
          <!-- don't use built-in 'removable' feature of Chip because it would remove the element even for page before -->
          <button @click="appState.reset_search_box(); appState.reset_search_results_and_map()"
            class="ml-1 h-4 w-4 flex items-center justify-center rounded-full bg-white text-xs text-gray-500">X</button>
        </Chip>
        <div class="flex-1"></div>
        <div v-if="appState.settings.search.search_type == 'similar_to_item' && appState.dev_mode && false">
          <span class="pr-2 text-sm text-gray-500">Weight:</span>
          <input
            v-model.number="appState.settings.search.internal_input_weight"
            class="w-10 text-sm text-gray-500"
            @keyup.enter="appState.request_search_results"
            @submit="appState.request_search_results" />
        </div>
      </div>
      <div v-if="['external_input'].includes(appState.settings.search.search_type)" class="flex h-9 flex-1 flex-row items-center">
        <input
          type="search"
          name="search"
          @keyup.enter="appState.request_search_results"
          v-model="appState.settings.search.all_field_query"
          autocomplete="off"
          :placeholder="
            appState.settings.search.search_type == 'external_input'
              ? `Describe what ${appState.settings.search.dataset_ids.length ? appState.datasets[appState.settings.search.dataset_ids[0]]?.entity_name || '' : ''} you want to find`
              : 'But more like this:'
          "
          class="h-full w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
      </div>
      <button v-if="appState.settings.search.search_type == 'external_input'"
        v-tooltip.bottom="{value: 'Search (list & map)', showDelay: 400}"
        class="ml-2 px-2 h-9 rounded-md shadow-sm border-gray-300 border bg-gray-100 hover:bg-blue-100/50 text-sm text-gray-500"
        @click="appState.request_search_results">
        <MagnifyingGlassIcon class="h-5 w-5"></MagnifyingGlassIcon>
      </button>
      <button v-if="appState.settings.search.search_type == 'external_input'"
        v-tooltip.bottom="{value: 'Answer question in a chat', showDelay: 400}"
        class="ml-2 px-2 h-9 rounded-md shadow-sm border-gray-300 border bg-gray-100 hover:bg-blue-100/50 text-sm text-gray-500"
        @click="appState.answer_question">
        <ChatBubbleLeftIcon class="h-5 w-5"></ChatBubbleLeftIcon>
      </button>
      <button
        v-if="appState.dev_mode"
        title="Negative Search"
        @click="show_negative_query_field = !show_negative_query_field"
        class="ml-1 w-8 rounded px-1 hover:bg-gray-100"
        :class="{
          'text-blue-600': show_negative_query_field,
          'text-gray-400': !show_negative_query_field,
        }">
        <MinusCircleIcon></MinusCircleIcon>
      </button>
      <button
        v-if="appState.dev_mode"
        @click="show_settings = !show_settings"
        class="ml-1 w-8 rounded px-1 hover:bg-gray-100"
        :class="{ 'text-blue-600': show_settings, 'text-gray-400': !show_settings }">
        <AdjustmentsHorizontalIcon></AdjustmentsHorizontalIcon>
      </button>
    </div>

    <div
      v-if="show_negative_query_field || appState.settings.search.all_field_query_negative"
      class="mt-2 h-9">
      <input
        type="search"
        name="negative_search"
        @keyup.enter="appState.request_search_results"
        v-model="appState.settings.search.all_field_query_negative"
        :placeholder="
          appState.settings.search.search_type == 'external_input'
            ? 'And optionally what should be excluded'
            : 'And less like this:'
        "
        class="h-full w-full rounded-md border-0 bg-red-100/50 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
    </div>

    <div v-if="query_uses_operators_and_meaning" class="mt-1 text-xs text-gray-400">
      The operators AND / OR are not supported for 'meaning' and 'hybrid' searches.<br>
      Please use filters and quoted phrases here or switch to 'keyword' search.
    </div>

    <div v-if="query_includes_other_quotes" class="mt-1 text-xs text-gray-400">
      Note: use double quotes instead of single quotes to search for phrases.
    </div>

    <div v-if="!use_smart_search" class="mt-2 ml-0 flex flex-row gap-1 items-center">
      <div class="flex flex-row items-center gap-0 h-6">
        <button class="border border-gray-300 rounded-l-md px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
          @click="appState.settings.search.search_algorithm = 'keyword'"
          v-tooltip="{ value: 'Use this to find specific words.\nSupports operators like AND / OR / NOT.', showDelay: 400 }"
          :class="{'text-blue-500': appState.settings.search.search_algorithm === 'keyword', 'text-gray-400': appState.settings.search.search_algorithm != 'keyword'}">
          Keyword
        </button>
        <button class="border border-gray-300  rounded-none px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
          @click="appState.settings.search.search_algorithm = 'vector'"
          v-tooltip="{ value: 'Use this to search for broader topics or information\nthat can be described in many different ways.\n\nNote: this might return almost all documents, but sorted\nso that the most relevant ones are at the top.\nOnly supports quoted phrases, not the AND / OR / NOT operators.', showDelay: 400 }"
          :class="{'text-blue-500': appState.settings.search.search_algorithm === 'vector', 'text-gray-400': appState.settings.search.search_algorithm != 'vector'}">
          Meaning
        </button>
        <button class="border border-gray-300 rounded-r-md  px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
          @click="appState.settings.search.search_algorithm = 'hybrid'"
          v-tooltip="{ value: 'Combines keyword and meaning search.\n\nNote: this might return almost all documents, but sorted\nso that the most relevant ones are at the top.\nOnly supports quoted phrases, not the AND / OR / NOT operators.', showDelay: 400 }"
          :class="{'text-blue-500': appState.settings.search.search_algorithm === 'hybrid', 'text-gray-400': appState.settings.search.search_algorithm != 'hybrid'}">
          Both
        </button>
      </div>
      <div class="flex-1"></div>
      <div class="flex flex-row items-center gap-0 h-6">
        <button class="border border-gray-300 rounded-md  px-1 text-sm font-['Lexend'] font-normal text-gray-400 hover:bg-gray-100"
          v-tooltip.bottom="{ value: 'Add filters and change search options', showDelay: 400 }"
          @click="(event) => { $refs.add_filter_menu.toggle(event) }">
          + Filter / Option
        </button>
        <OverlayPanel ref="add_filter_menu">
          <AddFilterMenu @close="$refs.add_filter_menu.hide()">
          </AddFilterMenu>
        </OverlayPanel>
      </div>
      <div class="flex-1"></div>
      <button
        v-if="appState.logged_in"
        @click="open_search_history_dialog()"
        v-tooltip.bottom="{ value: 'Search History', showDelay: 400 }"
        class="h-6 w-6 ml-1 rounded px-1 hover:bg-gray-100 text-gray-400">
        <ClockIcon></ClockIcon>
      </button><button
        v-if="appState.logged_in"
        @click="open_stored_maps_dialog()"
        v-tooltip.bottom="{ value: 'Stored Views', showDelay: 400 }"
        class="h-6 w-6 ml-1 rounded px-1 hover:bg-gray-100 text-gray-400">
        <BookmarkIcon></BookmarkIcon>
      </button>
    </div>
    <SearchFilterList v-if="!use_smart_search"></SearchFilterList>

    <!-- Parameters Area -->
    <div v-show="show_settings" class="mt-3">
      <div
        button
        @click="show_search_settings = !show_search_settings"
        class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1" />
        <span class="mx-2 flex-none text-sm text-gray-500"
          >Search {{ show_search_settings ? "v" : ">" }}</span
        >
        <hr class="flex-1" />
      </div>
      <div v-show="show_search_settings">
        <div
          v-if="!appState.settings.search.use_separate_queries"
          v-for="field in Object.keys(appState.settings.search.separate_queries)"
          class="flex items-center justify-between">
          <span class="text-sm text-gray-500">{{ field }}:</span>
          <input
            v-model="appState.settings.search.separate_queries[field].use_for_combined_search"
            type="checkbox" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Use separate queries:</span>
          <input v-model="appState.settings.search.use_separate_queries" type="checkbox" />
        </div>
        <div
          v-if="appState.settings.search.use_separate_queries"
          v-for="field in Object.keys(appState.settings.search.separate_queries)"
          class="flex items-center justify-between">
          <span class="text-sm text-gray-500">{{ field }}:</span>
          <input
            v-model.number="appState.settings.search.separate_queries[field].query"
            placeholder="positive"
            class="w-1/2 text-sm text-gray-500" />
          <input
            v-model.number="appState.settings.search.separate_queries[field].query_negative"
            placeholder="negative"
            class="w-1/2 text-sm text-gray-500" />
          Must:<input
            v-model="appState.settings.search.separate_queries[field].must"
            type="checkbox" />
          T.O.<input
            v-model.number="appState.settings.search.separate_queries[field].threshold_offset"
            type="range"
            min="-1.0"
            max="1.0"
            step="0.1"
            class="h-2 w-1/2 cursor-pointer appearance-none rounded-lg bg-gray-100" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Exclude items below thresholds:</span>
          <input
            v-model="appState.settings.search.use_similarity_thresholds"
            type="checkbox" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Use Reranking:</span>
          <input v-model="appState.settings.search.use_reranking" type="checkbox" />
        </div>
      </div>
      <div
        button
        @click="show_autocut_settings = !show_autocut_settings"
        class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1" />
        <span class="mx-2 flex-none text-sm text-gray-500"
          >Autocut {{ show_autocut_settings ? "v" : ">" }}</span
        >
        <hr class="flex-1" />
      </div>
      <div v-show="show_autocut_settings">
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Use Autocut:</span>
          <input v-model="appState.settings.search.use_autocut" type="checkbox" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Debug Autocut:</span>
          <input v-model="appState.debug_autocut" type="checkbox" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Autocut Strategy:</span>
          <select
            v-model="appState.settings.search.autocut_strategy"
            class="w-1/2 rounded border-transparent pb-1 pl-2 pr-8 pt-1 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
            <option v-for="item in available_autocut_strategies" :value="item.id" selected>
              {{ item.title }}
            </option>
          </select>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Autocut min. results:</span>
          <input
            v-model.number="appState.settings.search.autocut_min_results"
            class="w-1/2 text-sm text-gray-500" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Autocut min. score:</span>
          <input
            v-model.number="appState.settings.search.autocut_min_score"
            class="w-1/2 text-sm text-gray-500" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Autocut max. gradient:</span>
          <input
            v-model.number="appState.settings.search.autocut_max_relative_decline"
            class="w-1/2 text-sm text-gray-500" />
        </div>
      </div>
      <div
        button
        @click="show_vectorize_settings = !show_vectorize_settings"
        class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1" />
        <span class="mx-2 flex-none text-sm text-gray-500"
          >Vectorization {{ show_vectorize_settings ? "v" : ">" }}</span
        >
        <hr class="flex-1" />
      </div>
      <div v-show="show_vectorize_settings">
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Max. items for map:</span>
          <span class="text-sm text-gray-500">
            {{ appState.settings.search.max_items_used_for_mapping }}
          </span>
          <input
            v-model.number="appState.settings.search.max_items_used_for_mapping"
            type="range"
            min="10"
            max="10000"
            step="10"
            class="h-2 w-1/2 cursor-pointer appearance-none rounded-lg bg-gray-100" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Create projection using:</span>
          <select
            v-model="appState.settings.vectorize.map_vector_field"
            class="w-1/2 rounded border-transparent pb-1 pl-2 pr-8 pt-1 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
            <option value="w2v_vector" selected>Context-trained W2V Model</option>
            <option v-for="item in appState.available_vector_fields" :value="item[1]" selected>
              {{ item[1] }}
            </option>
          </select>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Secondary map vector:</span>
          <select
            v-model="appState.settings.vectorize.secondary_map_vector_field"
            class="w-1/2 rounded border-transparent pb-1 pl-2 pr-8 pt-1 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
            <option value="null" selected>None</option>
            <option value="w2v_vector" selected>Context-trained W2V Model</option>
            <option v-for="item in appState.available_vector_fields" :value="item[1]" selected>
              {{ item[1] }}
            </option>
          </select>
        </div>
        <!-- <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Tokenizer:</span>
          <select v-model="appState.settings.vectorize.tokenizer" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
              <option v-for="item in available_tokenizer" :value="item.id" selected>{{ item.title }}</option>
          </select>
        </div> -->
      </div>
      <div
        button
        @click="show_projection_settings = !show_projection_settings"
        class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1" />
        <span class="mx-2 flex-none text-sm text-gray-500"
          >Projection {{ show_projection_settings ? "v" : ">" }}</span
        >
        <hr class="flex-1" />
      </div>
      <div v-show="show_projection_settings">
        <div
          v-for="axis in [
            ['x_axis', 'X-Axis'],
            ['y_axis', 'Y-Axis'],
          ]"
          class="flex flex-row items-center justify-between">
          <span class="text-sm text-gray-500">{{ axis[1] }}</span>
          <select
            v-model="appState.settings.projection[axis[0]].type"
            class="rounded border-transparent pb-1 pl-2 pr-8 pt-1 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
            <option v-for="item in axis_type_options" :value="item.id" selected>
              {{ item.title }}
            </option>
          </select>
          <select
            v-model="appState.settings.projection[axis[0]].parameter"
            class="rounded border-transparent pb-1 pl-2 pr-8 pt-1 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
            <option
              v-if="['rank', 'score'].includes(appState.settings.projection[axis[0]])"
              value="">
              (no parameters)
            </option>
            <option
              v-if="appState.settings.projection[axis[0]].type === 'embedding'"
              value="primary">
              Primary
            </option>
            <option
              v-if="appState.settings.projection[axis[0]].type === 'embedding'"
              value="secondary">
              Secondary
            </option>
            <option
              v-if="appState.settings.projection[axis[0]].type === 'number_field'"
              v-for="ds_and_identifier in appState.available_number_fields"
              :value="ds_and_identifier[1]">
              {{ ds_and_identifier[1] }}
            </option>
          </select>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Polar Coordinates</span>
          <input
            v-model="appState.settings.projection.use_polar_coordinates"
            type="checkbox" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Invert X-Axis:</span>
          <input v-model="appState.settings.projection.invert_x_axis" type="checkbox" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Cluster hints:</span>
          <input
            v-model.number="appState.settings.projection.cluster_hints"
            class="w-1/2 text-sm text-gray-500" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Dim. Reducer:</span>
          <select
            v-model="appState.settings.projection.dim_reducer"
            class="w-1/2 rounded border-transparent pb-1 pl-2 pr-8 pt-1 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
            <option v-for="item in available_dim_reducers" :value="item.id" selected>
              {{ item.title }}
            </option>
          </select>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">UMAP n_neighbors:</span>
          <span class="text-sm text-gray-500">
            {{ appState.settings.projection.n_neighbors }}
          </span>
          <input
            v-model.number="appState.settings.projection.n_neighbors"
            type="range"
            min="1"
            max="100"
            step="1"
            class="h-2 w-1/2 cursor-pointer appearance-none rounded-lg bg-gray-100" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">UMAP min_dist:</span>
          <span class="text-sm text-gray-500">
            {{ appState.settings.projection.min_dist }}
          </span>
          <input
            v-model.number="appState.settings.projection.min_dist"
            type="range"
            min="0.01"
            max="0.99"
            step="0.01"
            class="h-2 w-1/2 cursor-pointer appearance-none rounded-lg bg-gray-100" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">UMAP n_epochs:</span>
          <span class="text-sm text-gray-500">
            {{ appState.settings.projection.n_epochs }}
          </span>
          <input
            v-model.number="appState.settings.projection.n_epochs"
            type="range"
            min="10"
            max="3000"
            step="10"
            class="h-2 w-1/2 cursor-pointer appearance-none rounded-lg bg-gray-100" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">UMAP metric:</span>
          <input
            v-model.number="appState.settings.projection.metric"
            class="w-1/2 text-sm text-gray-500" />
        </div>
      </div>
      <div
        button
        @click="show_rendering_settings = !show_rendering_settings"
        class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1" />
        <span class="mx-2 flex-none text-sm text-gray-500"
          >Clustering & Rendering {{ show_rendering_settings ? "v" : ">" }}</span
        >
        <hr class="flex-1" />
      </div>
      <div v-show="show_rendering_settings">
        <div
          v-for="param in rendering_parameters"
          class="flex flex-row items-center">
          <span class="w-20 text-sm text-gray-500">{{ param[1] }}</span>
          <div class="w-32">
            <select
              v-model="appState.settings.rendering[param[0]].type"
              class="w-full rounded border-transparent pb-1 pl-2 pr-8 pt-1 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
              <option v-for="item in rendering_type_options" :value="item.id" selected>
                {{ item.title }}
              </option>
            </select>
          </div>
          <div
            v-if="!['classifier'].includes(appState.settings.rendering[param[0]].type)"
            class="flex-1">
            <select
              v-model="appState.settings.rendering[param[0]].parameter"
              class="w-full rounded border-transparent pb-1 pl-2 pr-8 pt-1 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
              <option
                v-if="
                  ['score', 'fixed', 'rank', 'cluster_idx', 'origin_query_idx'].includes(
                    appState.settings.rendering[param[0]].type
                  )
                "
                value="">
                (no parameters)
              </option>
              <option
                v-if="
                  ['embedding', 'umap_perplexity'].includes(
                    appState.settings.rendering[param[0]].type
                  )
                "
                value="primary">
                Primary
              </option>
              <option
                v-if="
                  ['embedding', 'umap_perplexity'].includes(
                    appState.settings.rendering[param[0]].type
                  )
                ">
                Secondary
              </option>
              <option
                v-if="['number_field'].includes(appState.settings.rendering[param[0]].type)"
                v-for="ds_and_identifier in appState.available_number_fields"
                :value="ds_and_identifier[1]">
                {{ ds_and_identifier[1] }}
              </option>
            </select>
          </div>
          <CollectionAndVectorFieldSelection
            v-if="['classifier'].includes(appState.settings.rendering[param[0]].type)"
            v-model="appState.settings.rendering[param[0]].parameter"
            class="flex-1"/>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Cluster min. samples:</span>
          <input
            v-model.number="appState.settings.rendering.clusterizer_parameters.min_samples"
            class="w-1/2 text-sm text-gray-500" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Cluster min. size: (auto: -1)</span>
          <input
            v-model.number="
              appState.settings.rendering.clusterizer_parameters.min_cluster_size
            "
            class="w-1/2 text-sm text-gray-500" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Cluster max. size:</span>
          <input
            v-model.number="appState.settings.rendering.clusterizer_parameters.max_cluster_size"
            type="range"
            min="0.01"
            max="1.0"
            step="0.01"
            class="h-2 w-1/2 cursor-pointer appearance-none rounded-lg bg-gray-100" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Cluster 'leaf' mode (smaller clusters):</span>
          <input
            v-model="appState.settings.rendering.clusterizer_parameters.leaf_mode"
            type="checkbox" />
        </div>
      </div>
      <div
        button
        @click="show_frontend_settings = !show_frontend_settings"
        class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1" />
        <span class="mx-2 flex-none text-sm text-gray-500"
          >Frontend {{ show_other_settings ? "v" : ">" }}</span
        >
        <hr class="flex-1" />
      </div>
      <div v-show="show_frontend_settings">
        <div
          v-for="param in rendering_parameters"
          class="flex flex-row items-center justify-between">
          <span class="w-1/4 text-sm text-gray-500">{{ param[1] }}</span>
          <input
            v-model.number="appState.settings.frontend.rendering[param[0]].min"
            class="w-1/2 text-sm text-gray-500" />
          <input
            v-model.number="appState.settings.frontend.rendering[param[0]].max"
            class="w-1/2 text-sm text-gray-500" />
          <input
            v-model.number="appState.settings.frontend.rendering[param[0]].fallback"
            class="w-1/2 text-sm text-gray-500" />
          <input
            v-model="appState.settings.frontend.rendering[param[0]].gamma"
            class="w-1/2 text-sm text-gray-500" />
        </div>
        <div class="flex flex-row items-center justify-between">
          <span class="w-1/4 text-sm text-gray-500">Max. Opacity</span>
          <span class="text-sm text-gray-500">
            {{ appState.settings.frontend.rendering.max_opacity }}
          </span>
          <input
            v-model.number="appState.settings.frontend.rendering.max_opacity"
            type="range"
            min="0.0"
            max="1.0"
            step="0.05"
            class="h-2 w-1/2 cursor-pointer appearance-none rounded-lg bg-gray-100" />
        </div>
        <div class="flex flex-row items-center justify-between">
          <span class="w-1/4 text-sm text-gray-500">Shadow Opacity</span>
          <span class="text-sm text-gray-500">
            {{ appState.settings.frontend.rendering.shadow_opacity }}
          </span>
          <input
            v-model.number="appState.settings.frontend.rendering.shadow_opacity"
            type="range"
            min="0.0"
            max="1.0"
            step="0.01"
            class="h-2 w-1/2 cursor-pointer appearance-none rounded-lg bg-gray-100" />
        </div>
        <div class="flex flex-row items-center justify-between">
          <span class="w-1/4 text-sm text-gray-500">Point Size</span>
          <span class="text-sm text-gray-500">
            {{ appState.settings.frontend.rendering.point_size_factor }}
          </span>
          <input
            v-model.number="appState.settings.frontend.rendering.point_size_factor"
            type="range"
            min="0.1"
            max="5.0"
            step="0.1"
            class="h-2 w-1/2 cursor-pointer appearance-none rounded-lg bg-gray-100" />
        </div>
        <div class="flex flex-row items-center justify-between">
          <span class="w-1/4 text-sm text-gray-500">Style</span>
          <select
            v-model="appState.settings.frontend.rendering.style"
            class="w-1/2 rounded border-transparent pb-1 pl-2 pr-8 pt-1 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
            <option v-for="item in available_styles" :value="item.id" selected>
              {{ item.title }}
            </option>
          </select>
        </div>
      </div>
      <div
        button
        @click="show_other_settings = !show_other_settings"
        class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1" />
        <span class="mx-2 flex-none text-sm text-gray-500"
          >Other {{ show_other_settings ? "v" : ">" }}</span
        >
        <hr class="flex-1" />
      </div>
      <div v-show="show_other_settings">
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Ignore cache:</span>
          <input v-model="appState.ignore_cache" type="checkbox" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Store search history:</span>
          <input v-model="appState.store_search_history" type="checkbox" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Always load map:</span>
          <input v-model="appState.load_map_after_search" type="checkbox" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">Show timings:</span>
          <input v-model="appState.show_timings" type="checkbox" />
        </div>
      </div>
      <div class="flex flex-row gap-2">
        <input
          type="button"
          button
          @click="appState.request_search_results"
          class="rounded px-1 text-sm text-gray-500 shadow-sm hover:bg-blue-100 active:bg-blue-200"
          value="Rerun" />
        <input
          type="button"
          button
          @click="appState.reset_search_box"
          class="rounded px-1 text-sm text-gray-500 shadow-sm hover:bg-blue-100 active:bg-blue-200"
          value="Reset" />
      </div>
    </div>
  </div>
</template>
