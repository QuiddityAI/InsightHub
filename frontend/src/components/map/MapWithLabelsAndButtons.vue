<script setup>

import {
  CursorArrowRaysIcon,
  RectangleGroupIcon,
  PlusIcon,
  MinusIcon,
  ViewfinderCircleIcon,
  XMarkIcon,
  ArrowPathIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline"

// import OverlayPanel from "primevue/overlaypanel"

import BorderlessButton from "../widgets/BorderlessButton.vue"
import MapWithLabels from "./MapWithLabels.vue"
// import AddToCollectionButtons from "../../components/collections/AddToCollectionButtons.vue"

import { useToast } from 'primevue/usetoast';
import { debounce } from "../../utils/utils";
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store";

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
      generate_map_debounce: debounce(() => {
        this.collectionStore.generate_map()
      }, 100),
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
  },
  mounted() {
    const has_items = this.collectionStore.collection?.actual_classes[0].positive_count > 0
    const no_map_but_items = !this.collectionStore.collection?.map_metadata?.created_at && has_items
    const update_times_are_known = this.collectionStore.collection?.map_metadata?.created_at && this.collectionStore.collection?.items_last_changed
    let map_outdated = false
    if (update_times_are_known) {
      map_outdated = new Date(this.collectionStore.collection?.map_metadata.created_at) < new Date(this.collectionStore.collection?.items_last_changed)
    }
    if (no_map_but_items || (map_outdated && has_items)) {
      this.generate_map_debounce()
    } else {
      this.collectionStore.get_existing_projections()
    }
    this.eventBus.on("collection_items_changed_on_server", () => {
      this.generate_map_debounce()
    })
    this.eventBus.on("collection_filters_changed", ({filter_type}) => {
      if (filter_type === "collection_item_ids") {  // aka a selection or cluster
        this.collectionStore.generate_map()
      }
    })
    // could listen to filter changes, too, but that would trigger also with every single search query change etc.
    // instead, only when "cluster filters" are created, the map is regenerated
    // (generate_map() is called in appStateStore.narrow_down_on_cluster())
  },
  unmounted() {
    this.eventBus.off("collection_items_changed_on_server")
    this.eventBus.emit("reset_map")
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="relative">

    <MapWithLabels class="absolute w-full h-full"/>

    <div
      v-if="appState.map_id && mapState.map_parameters?.search.search_type === 'similar_to_item'"
      class="absolute bottom-6 right-[200px] flex flex-row items-center gap-2 rounded-md bg-white p-2 shadow-sm">
      <button
        v-tooltip.top="'Normal map with items arranged in island-like clusters'"
        @click="appState.set_two_dimensional_projection(); appState.request_search_results()"
        class="h-6 px-1 rounded hover:bg-gray-100"
        :class="{
          'text-blue-600': !appState.settings.projection.use_polar_coordinates,
          'text-gray-400': appState.settings.projection.use_polar_coordinates,
        }">
        Normal
      </button>
      <button
        v-tooltip.top="'Arrange items in a star shape around the most relevant one in the center'"
        @click="appState.set_polar_projection(); appState.request_search_results()"
        class="h-6 px-1 rounded hover:bg-gray-100"
        :class="{
          'text-blue-600': appState.settings.projection.use_polar_coordinates,
          'text-gray-400': !appState.settings.projection.use_polar_coordinates,
        }">
        Star-Shape
      </button>
    </div>


    <div
      v-if="mapState.selected_map_tool === 'lasso'"
      class="absolute bottom-6 right-4 flex flex-row justify-center gap-2 rounded-md bg-white p-2 shadow-sm">
      <button
        @click="mapState.selection_merging_mode = 'replace'"
        v-tooltip.top="{ value: 'Replace current selection with new one', showDelay: 400 }"
        class="h-6 w-6 rounded hover:bg-gray-100"
        :class="{
          'text-blue-600': mapState.selection_merging_mode === 'replace',
          'text-gray-400': mapState.selection_merging_mode !== 'replace',
        }">
        <ViewfinderCircleIcon></ViewfinderCircleIcon>
      </button>
      <button
        @click="mapState.selection_merging_mode = 'add'"
        v-tooltip.top="{ value: 'Add new selection to current one', showDelay: 400 }"
        class="h-6 w-6 rounded hover:bg-gray-100"
        :class="{
          'text-blue-600': mapState.selection_merging_mode === 'add',
          'text-gray-400': mapState.selection_merging_mode !== 'add',
        }">
        <PlusIcon></PlusIcon>
      </button>
      <button
        @click="mapState.selection_merging_mode = 'remove'"
        v-tooltip.left="{ value: 'Remove new selection from current one', showDelay: 400 }"
        class="mr-2 h-6 w-6 rounded hover:bg-gray-100"
        :class="{
          'text-blue-600': mapState.selection_merging_mode === 'remove',
          'text-gray-400': mapState.selection_merging_mode !== 'remove',
        }">
        <MinusIcon></MinusIcon>
      </button>
      <div class="h-6 w-6"></div>
    </div>
    <div
      class="absolute bottom-6 right-4 flex flex-col justify-center gap-2 rounded-md bg-white p-2 shadow-sm">
      <button
        @click="mapState.selected_map_tool = 'drag'; mapState.selection_merging_mode = 'replace'"
        v-tooltip.left="{ value: 'Navigate map by click and drag (normal mode)', showDelay: 400 }"
        class="h-6 w-6 rounded hover:bg-gray-100"
        :class="{
          'text-blue-600': mapState.selected_map_tool === 'drag',
          'text-gray-400': mapState.selected_map_tool !== 'drag',
        }">
        <CursorArrowRaysIcon></CursorArrowRaysIcon>
      </button>
      <button
        @click="mapState.selected_map_tool = 'lasso'"
        v-tooltip.left="{ value: 'Select items by drawing a line around them', showDelay: 400 }"
        class="h-6 w-6 rounded hover:bg-gray-100"
        :class="{
          'text-blue-600': mapState.selected_map_tool === 'lasso',
          'text-gray-400': mapState.selected_map_tool !== 'lasso',
        }">
        <RectangleGroupIcon></RectangleGroupIcon>
      </button>
    </div>

    <div
      v-if="mapState.selected_collection_item_ids.length"
      class="absolute bottom-6 right-48 flex flex-row items-center justify-center gap-2 rounded-md bg-white p-2 shadow-sm">
      <span class="mr-2 text-md text-gray-400">Selection:</span>
      <!-- <button
        @click="(event) => { $refs.add_selection_to_collection_overlay.toggle(event) }"
        class="px-2 rounded bg-gray-100 text-gray-400 hover:bg-blue-100/50">
        Add to Collection
      </button> -->
      <button
        @click="appState.narrow_down_on_selection()"
        class="px-2 rounded bg-gray-100 text-gray-400 hover:bg-blue-100/50">
        Show just selection
      </button>
      <BorderlessButton
        hover_color="hover:text-red-500" :default_padding="false" class="p-1"
        @click.stop="collectionStore.remove_items_from_collection(mapState.selected_collection_item_ids)"
        v-tooltip.top="{ value: 'Remove items from this collection', showDelay: 400 }">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </BorderlessButton>
      <button
        @click="mapState.reset_selection()"
        v-tooltip.top="{ value: 'Reset selection', showDelay: 400 }"
        class="h-6 w-6 rounded text-gray-400 hover:bg-red-100">
        <XMarkIcon></XMarkIcon>
      </button>
    </div>
    <!-- <OverlayPanel ref="add_selection_to_collection_overlay">
      <AddToCollectionButtons
        :multiple_items="true"
        @addToCollection="appState.add_selected_points_to_collection"
        @removeFromCollection="appState.remove_selected_points_from_collection">
      </AddToCollectionButtons>
    </OverlayPanel> -->

    <button class="absolute top-4 right-4 bg-white rounded-md p-1 shadow-md text-gray-600 hover:text-blue-500"
      v-tooltip.left="{ value: 'Re-generate the map from the current selection', showDelay: 400 }"
      @click="collectionStore.generate_map()">
      <ArrowPathIcon class="h-4 w-4"></ArrowPathIcon>
    </button>

    <div v-if="typeof collectionStore.collection?.map_metadata === 'object' && collectionStore.collection.map_metadata.projections_are_ready === false"
      class="absolute top-0 w-full h-full flex items-center justify-center backdrop-blur-sm">
      <div
        class="text-2xl text-gray-400 bg-white p-5 rounded-lg shadow-xl">
        Loading...
      </div>
    </div>

    <div v-else-if="mapState.per_point.x.length === 0"
      class="absolute top-0 w-full h-full flex items-center justify-center">
      <button v-if="!collectionStore.collection.agent_is_running"
        class=" bg-white rounded-md p-3 shadow-lg text-gray-600 hover:text-blue-500"
        v-tooltip.bottom="{ value: 'Generate a map from the current selection', showDelay: 400 }"
        @click="collectionStore.generate_map()">
        Generate Map
      </button>
      <div v-else
        class="text-2xl text-gray-400 bg-white p-5 rounded-lg shadow-xl">
        Loading...
      </div>
    </div>

  </div>
</template>

<style scoped>
</style>
