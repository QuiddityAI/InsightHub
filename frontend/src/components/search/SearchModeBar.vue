<script setup>
import {
  PencilIcon,
  NoSymbolIcon,
  ChevronUpIcon,
  StarIcon,
} from "@heroicons/vue/24/outline"

import Chip from "primevue/chip"

import BorderlessButton from "../widgets/BorderlessButton.vue";
import SearchFilterList from "./SearchFilterList.vue";
import SearchTaskExecutionSettings from "./SearchTaskExecutionSettings.vue";

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useCollectionStore } from '../../stores/collection_store';

const appState = useAppStateStore()
const collectionStore = useCollectionStore()

</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: ["edit_search_task"],
  data() {
    return {
      show_periodic_execution_settings: false,
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    search_settings() {
      return this.collectionStore.collection.most_recent_search_task?.settings
    },
    retrieval_parameters() {
      return this.collectionStore.collection.most_recent_search_task?.retrieval_parameters
    },
    dataset_name() {
      return this.appStateStore.datasets[this.search_settings.dataset_id]?.name
    }
  },
  mounted() {
    const task = this.collectionStore.collection.most_recent_search_task
    this.show_periodic_execution_settings = task?.is_saved || task?.run_on_new_items || false
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="w-full px-5 pt-3 pb-4 flex flex-col gap-4">

    <div class="flex flex-row justify-center relative">
      <BorderlessButton v-if="collectionStore.collection.search_task_navigation_history.length >= 2"
        @click="collectionStore.run_previous_search_task"
        v-tooltip.bottom="{value: $t('SearchModeBar.go-to-the-previous-search-result'), showDelay: 400}"
        class="absolute left-0">
        <ChevronUpIcon class="h-5 w-5" />
      </BorderlessButton>

      <div class="flex-none text-sm text-blue-400">
        {{ $t('SearchModeBar.search-in') }} <span class="font-bold italic text-blue-400">{{ dataset_name }}</span>
      </div>

      <BorderlessButton class="absolute right-0"
        @click="collectionStore.exit_search_mode"
        v-tooltip.bottom="{value: $t('SearchModeBar.exit-search-tooltip'), showDelay: 400}">
        <NoSymbolIcon class="h-5 w-5 inline" /> {{ $t('SearchModeBar.exit') }}
      </BorderlessButton>
    </div>

    <button class="border border-gray-200 rounded-lg shadow-md bg-white hover:border-blue-300"
      @click="$emit('edit_search_task')">
      <div class="flex flex-row items-center pl-3 pr-1 py-1">

        <span v-if="search_settings.search_type === 'external_input' && search_settings.user_input"
          class="text-gray-600 font-medium text-left">
          {{ search_settings.user_input || $t('SearchModeBar.no-search-query') }}
        </span>
        <span v-if="search_settings.search_type === 'external_input' && !search_settings.user_input"
          class="text-gray-600 font-medium text-left">
          All Items
        </span>
        <span v-if="search_settings.search_type === 'random_sample'"
          class="text-gray-600 font-medium text-left">
          All Items / Random Subset
        </span>
        <span v-if="search_settings.search_type === 'similar_to_item'"
          class="text-gray-600 font-medium text-left">
          Similar to: {{ search_settings.origin_name || '?' }}
        </span>

        <div class="flex-1"></div>

        <BorderlessButton @click.stop="show_periodic_execution_settings = !show_periodic_execution_settings" class="py-1"
          :highlighted="show_periodic_execution_settings"
          v-tooltip.bottom="{value: $t('SearchModeBar.save-execute-periodically'), showDelay: 400}">
          <StarIcon class="h-5 w-5 inline" />
        </BorderlessButton>
        <BorderlessButton @click.stop="$emit('edit_search_task')" class="py-1"
          v-tooltip.bottom="{value: $t('SearchModeBar.edit-the-search-query-and-filters'), showDelay: 400}">
          <PencilIcon class="h-5 w-5 inline" />
        </BorderlessButton>

      </div>

    </button>

    <div class="flex flex-row flex-wrap gap-2">
      <Chip v-if="(search_settings.user_input || retrieval_parameters.keyword_query) && search_settings.search_type === 'external_input'">
        <span class="text-xs font-normal text-gray-500">
          Mode: {{ search_settings.retrieval_mode }}
        </span>
      </Chip>
      <Chip v-if="search_settings.ranking_settings">
        <span class="text-xs font-normal text-gray-500">
          Sort: {{ search_settings.ranking_settings.title }}
        </span>
      </Chip>
      <Chip v-if="search_settings.result_language">
        <span class="text-xs font-normal text-gray-500">
          {{ search_settings.result_language }}
          <!-- {{ languages.find(d => d.code === search_settings.result_language).flag }} -->
        </span>
      </Chip>
      <Chip v-if="(search_settings.user_input || retrieval_parameters.keyword_query)
          && search_settings.search_type === 'external_input'
          && search_settings.retrieval_mode !== 'vector'">
        <span class="text-xs font-normal text-gray-500">
            {{ search_settings.auto_relax_query ? 'Auto Relax' : 'No Auto Relax' }}
        </span>
      </Chip>
      <Chip v-if="search_settings.user_input !== retrieval_parameters.keyword_query">
        <span class="text-xs font-normal text-gray-500">
          Generated keyword query: '{{ retrieval_parameters.keyword_query }}'
        </span>
      </Chip>

      <SearchFilterList
        :filters="retrieval_parameters.filters || []"
        :removable="false"
        class="">
      </SearchFilterList>
    </div>



    <div v-if="show_periodic_execution_settings" class="flex flex-row items-center gap-4 mb-1">
      <SearchTaskExecutionSettings :task="collectionStore.collection.most_recent_search_task">
      </SearchTaskExecutionSettings>
    </div>

  </div>
</template>

<style scoped>
</style>
