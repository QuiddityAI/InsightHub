<script setup>

import {
  CursorArrowRaysIcon,
  RectangleGroupIcon,
  PlusIcon,
  MinusIcon,
  ViewfinderCircleIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline"

import Button from 'primevue/button';
import OverlayPanel from "primevue/overlaypanel"

import MapWithLabels from "./MapWithLabels.vue"
import AddToCollectionButtons from "../../components/collections/AddToCollectionButtons.vue"

import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="absolute h-screen w-screen">

    <MapWithLabels class="absolute top-0 h-screen w-screen"/>

    <div
      v-if="appState.map_id && appState.settings.search.search_type === 'similar_to_item'"
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
      v-if="mapState.visibility_filters.length"
      class="absolute bottom-6 right-48 flex flex-row items-center justify-center gap-2 rounded-md bg-white p-2 shadow-sm">
      <span class="mr-2 text-md text-gray-400">Selection:</span>
      <button
        @click="(event) => { $refs.add_selection_to_collection_overlay.toggle(event) }"
        class="px-2 rounded bg-gray-100 text-gray-400 hover:bg-blue-100/50">
        Add to Collection
      </button>
      <button
        @click="appState.narrow_down_on_selection(appState.visible_result_ids)"
        class="px-2 rounded bg-gray-100 text-gray-400 hover:bg-blue-100/50">
        Recluster
      </button>
      <button
        @click="mapState.reset_visibility_filters()"
        class="h-6 w-6 rounded text-gray-400 hover:bg-red-100">
        <XMarkIcon></XMarkIcon>
      </button>
    </div>
    <OverlayPanel ref="add_selection_to_collection_overlay">
      <AddToCollectionButtons
        :multiple_items="true"
        @addToCollection="appState.add_selected_points_to_collection"
        @removeFromCollection="appState.remove_selected_points_from_collection">
      </AddToCollectionButtons>
    </OverlayPanel>

  </div>
</template>

<style scoped>
</style>
