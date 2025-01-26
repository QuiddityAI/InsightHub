<script setup>

import Checkbox from 'primevue/checkbox';
import Message from 'primevue/message';
import { useToast } from 'primevue/usetoast';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()
</script>

<script>

export default {
  inject: [],
  props: ["task"],
  emits: [],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
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

  <div class="flex flex-col gap-1">
    <div class="flex flex-row items-center gap-3">

      <div class="flex flex-row items-center gap-1">
        <Checkbox v-model="task.is_saved"
          :inputId="`is_saved_${task.id}`" size="small" :binary="true" class="scale-75"
          @change="collectionStore.commit_search_task_execution_settings(task)" />
        <label :for="`is_saved_${task.id}`" class="text-sm text-gray-500">
          {{ $t('SearchTaskExecutionSettings.save') }}
        </label>
      </div>

      <div class="flex flex-row items-center gap-1" v-if="appState.user.is_staff">
        <Checkbox v-model="task.run_on_new_items"
          :inputId="`run_on_new_items_${task.id}`" size="small" :binary="true" class="scale-75"
          @change="collectionStore.commit_search_task_execution_settings(task)" />
        <label :for="`run_on_new_items_${task.id}`" class="text-sm text-gray-500">
          {{ $t('SearchTaskExecutionSettings.run-on-new-items', [collectionStore.entity_name_plural]) }}
        </label>
      </div>

    </div>

    <Message v-if="task.run_on_new_items && task.settings.retrieval_mode !== 'keyword'" severity="warn">
      {{ $t('SearchTaskExecutionSettings.only-available-for-keyword-searches') }}
    </Message>
  </div>

</template>

<style scoped>
</style>
